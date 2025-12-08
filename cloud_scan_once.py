# cloud_scan_once.py
"""
GitHub Actions에서 실행할 '단발성 스캐너'
- 오늘 기준 한 번 S&P500 + NASDAQ100 전체를 스캔하고
  조건에 맞는 종목이 있으면 텔레그램으로 차트 전송
- main.py의 함수들을 재사용
"""

from datetime import datetime

from main import (
    init_tickers,
    combined,
    check_symbol_and_alert,
)

def run_once():
    # 티커 목록 로드
    init_tickers()
    now = datetime.now()

    # 전체 지수/종목 한 번씩 검사
    for index_name, symbol in combined:
        check_symbol_and_alert(index_name, symbol, now)

if __name__ == "__main__":
    run_once()
