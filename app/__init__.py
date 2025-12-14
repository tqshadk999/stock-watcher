# app/notifier.py
from __future__ import annotations

import os
import requests


def _get_token_chat():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다. (GitHub Secrets/환경변수 확인)")
    return token, chat_id


def send_message(text: str, parse_mode: str | None = None) -> None:
    token, chat_id = _get_token_chat()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    r = requests.post(url, data=payload, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram sendMessage 실패: {r.status_code} / {r.text}")


def send_photo(photo_bytes: bytes, caption: str | None = None, parse_mode: str | None = None) -> None:
    token, chat_id = _get_token_chat()
    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    if parse_mode:
        data["parse_mode"] = parse_mode

    files = {"photo": ("chart.png", photo_bytes)}
    r = requests.post(url, data=data, files=files, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram sendPhoto 실패: {r.status_code} / {r.text}")

