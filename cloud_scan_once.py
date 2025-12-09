# app/cloud_scan_once.py
"""
GitHub Actions에서 실행하는 단발성 스캐너
- 실행 즉시 "스캐너 동작 중" 텔레그램 메시지를 발송
- S&P500 / NASDAQ100 / 즐겨찾기 종목 스캔
"""

import os
from datetime import datetime
from notifier import bot  # 텔레그램 전송
from main import (
    init_tickers,
    combined,
    check_symbol_and_alert,
)

def run_once():
    # GitHub Actions에서 동작 확인용 1회 메시지
    bot.send_message(
        chat_id=os.getenv("CHAT_ID"),
        text="☁️ GitHub Actions 스캐너 실행됨 (cloud_scan_once.py)"
    )

    # 티커 목록 초기화
    init_tickers()
    now = datetime.now()

    # 전체 종목 스캔 1회 실행
    for index_name, symbol in combined:
        check_symbol_and_alert(index_name, symbol, now)


if __name__ == "__main__":
    run_once()
