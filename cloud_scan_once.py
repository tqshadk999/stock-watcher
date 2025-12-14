# app/cloud_scan_once.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from .notifier import send_message
from .main import run_scheduled_once


KST = timezone(timedelta(hours=9))


def main():
    now_kst = datetime.now(KST)

    # ✅ 액션이 실제로 실행됐는지 무조건 확인용 테스트 메시지(매번)
    # 원치 않으면 아래 1줄 주석 처리하면 됩니다.
    send_message(
        token_env="TELEGRAM_TOKEN",
        chat_id_env="CHAT_ID",
        text=f"✅ GitHub Actions 실행됨 (KST {now_kst:%Y-%m-%d %H:%M})"
    )

    # 실제 스캔/알림 1회 실행
    run_scheduled_once(now_kst)


if __name__ == "__main__":
    main()
