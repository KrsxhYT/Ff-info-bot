import os
import re
import requests
import telebot
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import uvicorn
from datetime import datetime

# ============================
#  CONFIGURATION & LOGGING
# ============================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7710890735:AAGx-FLcjXdK4GXOFRovjfh4fa2KWvqd6I8")
API_BASE_URL = "https://info-ob49.vercel.app/api/account/"
REQUEST_TIMEOUT = 15

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI(title="Free Fire Info Bot API", version="1.0.0")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================
#  MODELS
# ============================
class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# ============================
#  UTILITY FUNCTIONS
# ============================
def escape_markdown(text: Any) -> str:
    """Escape special MarkdownV2 characters"""
    if text is None:
        return "None"
    
    # Convert to string and escape special characters
    text_str = str(text)
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text_str = text_str.replace(char, f'\\{char}')
    return text_str

def safe_get(data: Dict[str, Any], *keys, default: Any = "N/A") -> Any:
    """Safely get nested dictionary values"""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return default if current is None else current

# ============================
#  FORMATTING FUNCTIONS
# ============================
def format_player_info(data: Dict[str, Any]) -> str:
    """Format player information into a readable Markdown message"""
    
    # Basic Info
    basic = data.get("basicInfo", {})
    clan = data.get("clanBasicInfo", {})
    captain = data.get("captainBasicInfo", {})
    credit = data.get("creditScoreInfo", {})
    pet = data.get("petInfo", {})
    social = data.get("socialInfo", {})
    
    sections = []
    
    # 👤 Basic Info
    basic_section = f"""
👤 *Basic Info*
• Name: `{escape_markdown(safe_get(basic, "nickname", default="Unknown"))}`
• UID: `{safe_get(basic, "accountId", default="N/A")}`
• Region: `{safe_get(basic, "region", default="N/A")}`
• Level: `{safe_get(basic, "level", default="0")}`
• Likes: `{safe_get(basic, "liked", default="0")}`
• EXP: `{safe_get(basic, "exp", default="0")}`
• BR Rank: `{safe_get(basic, "brRank", default="N/A")}`
• CS Rank: `{safe_get(basic, "csRank", default="N/A")}`
• Max BR: `{safe_get(basic, "brMaxRank", default="N/A")}`
• Max CS: `{safe_get(basic, "csMaxRank", default="N/A")}`
• Title ID: `{safe_get(basic, "title", default="N/A")}`
• Banner ID: `{safe_get(basic, "bannerId", default="N/A")}`
• Avatar ID: `{safe_get(basic, "headPic", default="N/A")}`
• Version: `{escape_markdown(safe_get(basic, "releaseVersion", default="N/A"))}`
"""
    sections.append(basic_section.strip())
    
    # 🛡️ Guild Info (if exists)
    if clan.get("clanId"):
        clan_section = f"""
🛡️ *Guild Info*
• Name: `{escape_markdown(safe_get(clan, "clanName", default="None"))}`
• ID: `{safe_get(clan, "clanId", default="N/A")}`
• Level: `{safe_get(clan, "clanLevel", default="0")}`
• Members: `{safe_get(clan, "memberNum", default="0")}/{safe_get(clan, "capacity", default="0")}`
• Captain UID: `{safe_get(clan, "captainId", default="N/A")}`
"""
        sections.append(clan_section.strip())
    
    # 👑 Guild Captain (if exists)
    if captain.get("accountId"):
        captain_section = f"""
👑 *Guild Captain*
• Name: `{escape_markdown(safe_get(captain, "nickname", default="N/A"))}`
• UID: `{safe_get(captain, "accountId", default="N/A")}`
• Region: `{safe_get(captain, "region", default="N/A")}`
• Level: `{safe_get(captain, "level", default="0")}`
• Likes: `{safe_get(captain, "liked", default="0")}`
• BR Rank: `{safe_get(captain, "brRank", default="N/A")}`
• CS Rank: `{safe_get(captain, "csRank", default="N/A")}`
• BR Points: `{safe_get(captain, "brRankingPoints", default="0")}`
• CS Points: `{safe_get(captain, "csRankingPoints", default="0")}`
"""
        sections.append(captain_section.strip())
    
    # 🐾 Pet Info (if exists)
    if pet.get("id"):
        pet_section = f"""
🐾 *Pet Info*
• Pet ID: `{safe_get(pet, "id", default="N/A")}`
• Level: `{safe_get(pet, "level", default="0")}`
• EXP: `{safe_get(pet, "exp", default="0")}`
• Skin ID: `{safe_get(pet, "skinId", default="N/A")}`
• Skill ID: `{safe_get(pet, "selectedSkillId", default="N/A")}`
"""
        sections.append(pet_section.strip())
    
    # ⭐ Credit Score (if exists)
    if credit.get("creditScore"):
        credit_section = f"""
⭐ *Credit Score*
• Score: `{safe_get(credit, "creditScore", default="0")}`
• Summary: `{safe_get(credit, "periodicSummaryStartTime", default="N/A")} to {safe_get(credit, "periodicSummaryEndTime", default="N/A")}`
• Reward State: `{safe_get(credit, "rewardState", default="N/A")}`
"""
        sections.append(credit_section.strip())
    
    # 📱 Social Info
    social_section = f"""
📱 *Social*
• BR Public: `{safe_get(social, "brRankShow", default="N/A")}`
• CS Public: `{safe_get(social, "csRankShow", default="N/A")}`
• Bio: `{escape_markdown(safe_get(social, "signature", default="None"))}`
"""
    sections.append(social_section.strip())
    
    # Footer
    sections.append(f"⚡ *Last Updated:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    sections.append("👨‍💻 *Powered by:* @abbas_tech_india")
    
    return "\n\n".join(sections)

def fetch_player_info(uid: str, region: str) -> Dict[str, Any]:
    """Fetch player information from the API"""
    url = f"{API_BASE_URL}?uid={uid}&region={region}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        if not isinstance(data, dict):
            raise ValueError("Invalid response format")
        
        if not data.get("basicInfo"):
            raise ValueError("Player not found")
        
        return data
        
    except requests.exceptions.Timeout:
        raise Exception("Request timeout. Please try again.")
    except requests.exceptions.ConnectionError:
        raise Exception("Connection error. Please check your internet.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception("Player not found with given UID and region.")
        else:
            raise Exception(f"API Error: {e.response.status_code}")
    except ValueError as e:
        raise Exception(str(e))
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")

# ============================
#  BOT MESSAGE HANDLING
# ============================
def send_telegram_message(chat_id: int, text: str, parse_mode: str = "MarkdownV2"):
    """Send message to Telegram with error handling"""
    try:
        bot.send_message(chat_id, text, parse_mode=parse_mode)
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        # Try sending without markdown if there's a parsing error
        try:
            bot.send_message(chat_id, text.replace('`', '').replace('*', ''), parse_mode=None)
        except:
            pass

# ============================
#  FASTAPI ENDPOINTS
# ============================
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Free Fire Info Bot",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/webhook", response_model=APIResponse, tags=["Bot"])
async def telegram_webhook(update: TelegramUpdate):
    """Handle Telegram webhook updates"""
    try:
        # Determine the message source
        message = update.message or update.edited_message
        if not message:
            logger.info(f"Received non-message update: {update.update_id}")
            return APIResponse(success=True)
        
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        user_id = message.get("from", {}).get("id")
        
        logger.info(f"Received message from {user_id} in chat {chat_id}: {text}")
        
        # Handle non-command messages
        if not text.startswith("/"):
            return APIResponse(success=True)
        
        # Handle /start and /help commands
        if text.startswith(("/start", "/help")):
            help_text = """
🎮 *Free Fire Player Info Bot*

*Available Commands:*
`/get <region> <uid>` - Get player information
`/help` - Show this help message

*Usage Example:*
`/get ind 10000001`

*Supported Regions:* ind, br, id, etc.

*Note:* UID is your Free Fire account ID

👨‍💻 *Developer:* @abbas_tech_india
"""
            send_telegram_message(chat_id, escape_markdown(help_text))
            return APIResponse(success=True)
        
        # Handle /get command
        if text.startswith("/get"):
            parts = text.split()
            
            if len(parts) < 3:
                send_telegram_message(
                    chat_id, 
                    "❌ *Invalid Format!*\n\n"
                    "*Correct Usage:*\n"
                    "`/get <region> <uid>`\n\n"
                    "*Example:*\n"
                    "`/get ind 10000001`"
                )
                return APIResponse(success=True)
            
            region = parts[1].lower()
            uid = parts[2]
            
            # Validate UID (numeric check)
            if not uid.isdigit():
                send_telegram_message(chat_id, "❌ *Invalid UID!* UID must contain only numbers.")
                return APIResponse(success=True)
            
            # Send loading message
            try:
                loading_msg = bot.send_message(
                    chat_id, 
                    "⏳ *Fetching player information...*", 
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.error(f"Failed to send loading message: {e}")
                loading_msg = None
            
            try:
                # Fetch player data
                player_data = fetch_player_info(uid, region)
                
                # Format and send response
                formatted_info = format_player_info(player_data)
                
                if loading_msg:
                    bot.edit_message_text(
                        formatted_info,
                        chat_id=chat_id,
                        message_id=loading_msg.message_id,
                        parse_mode="MarkdownV2"
                    )
                else:
                    send_telegram_message(chat_id, formatted_info)
                
                logger.info(f"Successfully fetched info for UID: {uid}, Region: {region}")
                
            except Exception as e:
                error_msg = f"❌ *Error:* `{escape_markdown(str(e))}`"
                
                if loading_msg:
                    bot.edit_message_text(
                        error_msg,
                        chat_id=chat_id,
                        message_id=loading_msg.message_id,
                        parse_mode="MarkdownV2"
                    )
                else:
                    send_telegram_message(chat_id, error_msg)
                
                logger.error(f"Failed to fetch player info: {e}")
            
            return APIResponse(success=True)
        
        # Unknown command
        send_telegram_message(
            chat_id,
            "❌ *Unknown Command!*\n\n"
            "Use `/help` to see available commands."
        )
        return APIResponse(success=True)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return APIResponse(
            success=False,
            message="Internal server error"
        )

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_status": "online" if BOT_TOKEN else "offline"
    }

# ============================
#  ERROR HANDLERS
# ============================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "success": False,
        "error": "Internal server error",
        "message": str(exc) if str(exc) else "Unknown error occurred"
    }

# ============================
#  APPLICATION STARTUP
# ============================
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Starting Free Fire Info Bot API...")
    logger.info(f"Bot initialized: {bot.get_me().username if BOT_TOKEN else 'No token'}")
    logger.info(f"Server running on port {os.environ.get('PORT', 8000)}")

# ============================
#  MAIN ENTRY POINT
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    # Log startup info
    logger.info(f"Starting server on port {port}")
    logger.info(f"Bot Token: {'Set' if BOT_TOKEN and BOT_TOKEN != '7710890735:AAGx-FLcjXdK4GXOFRovjfh4fa2KWvqd6I8' else 'Using default (for testing)'}")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
