# app/cloud_scan_once.py
from datetime import datetime
import os

from app.notifier import send_message
from app.main import run_cloud_once


def main():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다. (GitHub Secrets 확인)")

    # ✅ 1) Actions 실행되면 무조건 테스트 메시지 1번 발송
    now = datetime.now()
    send_message(token, chat_id, f"✅ GitHub Actions 실행됨: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # ✅ 2) 스캐너 1회 실행
    run_cloud_once(now)


if __name__ == "__main__":
    main()
