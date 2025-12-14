# app/notifier.py
from __future__ import annotations

import os
import requests


def _get_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"{name} 환경변수가 비어 있습니다.")
    return v


def send_message(token_env: str, chat_id_env: str, text: str, parse_mode: str | None = None):
    token = _get_env(token_env)
    chat_id = _get_env(chat_id_env)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    r = requests.post(url, data=payload, timeout=30)
    r.raise_for_status()
