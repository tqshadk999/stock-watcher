# app/main.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from app.notifier import send_message
from app.scanner import scan_themes_top10, format_theme_message


def _now_kst() -> datetime:
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))


def run_cloud_once() -> None:
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN / CHAT_ID 가 비어있습니다 (GitHub Secrets 또는 환경변수 확인).")

    now = _now_kst()

    # 1) 실행 시작 알림(원하면 제거 가능)
    send_message(
        token,
        chat_id,
        "✅ [Stock Watcher] Cloud Scan 시작",
    )

    # 2) 테마별 스캔
    results = scan_themes_top10(now)

    # 3) 결과 전송
    text = format_theme_message(results, now)
    send_message(token, chat_id, text, parse_mode="Markdown")
