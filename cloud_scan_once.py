# cloud_scan_once.py
"""
GitHub Actions에서 한 번 실행할 때 사용하는 스캐너.

- S&P500 + NASDAQ100 전체를 오늘 기준으로 한 번 스캔
- 조건에 맞는 종목은 차트와 함께 텔레그램 전송
- 조건에 맞는 종목이 하나도 없어도
  "☁️ GitHub Actions 스캔 시작/완료" 메시지를 보내서
  사용자가 작동 여부를 확인할 수 있게 함
"""

from datetime import datetime
import os
from dotenv import load_dotenv

from main import (
    init_tickers,
    combined,
    check_symbol_and_alert,
    TELEGRAM_TOKEN,
    CHAT_ID,
)
from notifier import send_message

# GitHub 환경에서도 .env가 있으면 같이 로드 (없어도 무시)
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


def run_once():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN / CHAT_ID 환경변수가 설정되어 있지 않습니다.")

    # 티커 로드
    init_tickers()
    now = datetime.utcnow()

    # 시작 알림
    start_msg = f"☁️ GitHub Actions 스캔 시작\n시간(UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}"
    send_message(TELEGRAM_TOKEN, CHAT_ID, start_msg)

    # 전체 종목 한 번씩 검사
    for index_name, symbol in combined:
        check_symbol_and_alert(index_name, symbol, now)

    end_msg = "✅ GitHub Actions 스캔 완료"
    send_message(TELEGRAM_TOKEN, CHAT_ID, end_msg)


if __name__ == "__main__":
    run_once()
