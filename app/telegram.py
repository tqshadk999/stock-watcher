# app/telegram.py
import os
import requests


def send_message(text: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError(
            f"❌ TELEGRAM ENV NOT SET\n"
            f"BOT_TOKEN={token}\n"
            f"CHAT_ID={chat_id}"
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
