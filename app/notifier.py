# app/notifier.py
import requests


def send_message(token: str, chat_id: str, text: str, parse_mode: str | None = None) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    r = requests.post(url, data=payload, timeout=30)
    r.raise_for_status()


def send_photo(token: str, chat_id: str, photo_bytes: bytes, caption: str | None = None, parse_mode: str | None = None) -> None:
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    if parse_mode:
        data["parse_mode"] = parse_mode

    files = {"photo": ("chart.png", photo_bytes)}
    r = requests.post(url, data=data, files=files, timeout=60)
    r.raise_for_status()
