import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text: str):
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN or CHAT_ID not set")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    resp = requests.post(url, json=payload, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(
            f"❌ Telegram send failed: {resp.status_code} {resp.text}"
        )
