# notifier.py
import requests
import logging

logger = logging.getLogger(__name__)


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"telegram send_message failed: {e}")
        return False


def send_photo(token: str, chat_id: str, image_bytes: bytes, caption: str = "", parse_mode: str = "Markdown") -> bool:
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        files = {"photo": ("chart.png", image_bytes, "image/png")}
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": parse_mode}
        r = requests.post(url, files=files, data=data, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"telegram send_photo failed: {e}")
        return False
