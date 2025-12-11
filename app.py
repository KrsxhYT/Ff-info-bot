import os
import re
import requests
import telebot
from fastapi import FastAPI
from pydantic import BaseModel

# ============================
#  BOT TOKEN
# ============================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7710890735:AAGx-FLcjXdK4GXOFRovjfh4fa2KWvqd6I8")
bot = telebot.TeleBot(BOT_TOKEN)

app = FastAPI()

# ============================
#  MARKDOWN ESCAPER
# ============================
def escape_md(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text or ""))

# ============================
#  TELEGRAM UPDATE MODEL
# ============================
class TelegramUpdate(BaseModel):
    update_id: int
    message: dict = None
    edited_message: dict = None

# ============================
#  HELPER FUNCTIONS
# ============================
def format_ff_info(data: dict) -> str:
    b = data["basicInfo"]
    c = data.get("clanBasicInfo", {})
    cap = data.get("captainBasicInfo", {})
    cr = data.get("creditScoreInfo", {})
    pet = data.get("petInfo", {})
    s = data.get("socialInfo", {})

    text = f"""
👤 *Basic Info*
• Name: `{escape_md(b.get("nickname"))}`
• UID: `{b.get("accountId")}`
• Region: `{b.get("region")}`
• Level: `{b.get("level")}`
• Likes: `{b.get("liked")}`
• EXP: `{b.get("exp")}`
• BR Rank: `{b.get("brRank")}`
• CS Rank: `{b.get("csRank")}`
• Max BR: `{b.get("brMaxRank")}`
• Max CS: `{b.get("csMaxRank")}`
• Title ID: `{b.get("title")}`
• Banner ID: `{b.get("bannerId")}`
• Avatar ID: `{b.get("headPic")}`
• Version: `{escape_md(b.get("releaseVersion"))}`

🛡️ *Guild Info*
• Name: `{escape_md(c.get("clanName", 'None'))}`
• ID: `{c.get("clanId")}`
• Level: `{c.get("clanLevel")}`
• Members: `{c.get("memberNum")}/{c.get("capacity")}`
• Captain UID: `{c.get("captainId")}`

👑 *Guild Captain*
• Name: `{escape_md(cap.get("nickname", 'N/A'))}`
• UID: `{cap.get("accountId")}`
• Region: `{cap.get("region")}`
• Level: `{cap.get("level")}`
• Likes: `{cap.get("liked")}`
• BR Rank: `{cap.get("brRank")}`
• CS Rank: `{cap.get("csRank")}`
• BR Points: `{cap.get("brRankingPoints")}`
• CS Points: `{cap.get("csRankingPoints")}`

🐾 *Pet Info*
• Pet ID: `{pet.get("id")}`
• Level: `{pet.get("level")}`
• EXP: `{pet.get("exp")}`
• Skin ID: `{pet.get("skinId")}`
• Skill ID: `{pet.get("selectedSkillId")}`

⭐ *Credit Score*
• Score: `{cr.get("creditScore")}`
• Summary: `{cr.get("periodicSummaryStartTime")} to {cr.get("periodicSummaryEndTime")}`
• Reward State: `{cr.get("rewardState")}`

📱 *Social*
• BR Public: `{s.get("brRankShow")}`
• CS Public: `{s.get("csRankShow")}`
• Bio: `{escape_md(s.get("signature", 'None'))}`

⚡ by @abbas_tech_india
"""
    return text

def send_message(chat_id: int, text: str):
    bot.send_message(chat_id, text, parse_mode="MarkdownV2")

# ============================
#  FASTAPI WEBHOOK
# ============================
@app.post("/api/webhook")
async def telegram_webhook(update: TelegramUpdate):
    message = update.message or update.edited_message
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Only respond to commands to avoid wasting messages
    if not text.startswith("/"):
        # Ignore non-command messages
        return {"ok": True}

    if text.startswith("/start") or text.startswith("/help"):
        help_text = """
🥳 *Free Fire Player Info Bot*

🚀 Use command:  
`/get {region} {uid}`

🎮 Example:  
`/get ind 10000001`

👨‍💻 Powered by @abbas_tech_india
"""
        send_message(chat_id, escape_md(help_text))
        return {"ok": True}

    if text.startswith("/get"):
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, escape_md("❌ Usage: `/get {region} {uid}`"))
            return {"ok": True}

        region = parts[1].lower()
        uid = parts[2]

        loading_msg = bot.send_message(chat_id, escape_md("⏳ Fetching Free Fire Account Info..."), parse_mode="MarkdownV2")

        try:
            url = f"https://info-ob49.vercel.app/api/account/?uid={uid}&region={region}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                bot.edit_message_text(f"❌ API Error: {response.status_code}", chat_id=chat_id, message_id=loading_msg.message_id)
                return {"ok": True}

            data = response.json()
            if not data.get("basicInfo"):
                bot.edit_message_text("❌ No player found for this UID.", chat_id=chat_id, message_id=loading_msg.message_id)
                return {"ok": True}

            bot.edit_message_text(format_ff_info(data), chat_id=chat_id, message_id=loading_msg.message_id, parse_mode="MarkdownV2")
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id=chat_id, message_id=loading_msg.message_id)

        return {"ok": True}

    # No reply to other commands or messages to avoid waste
    return {"ok": True}

# ============================
#  START SERVER
# ============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
