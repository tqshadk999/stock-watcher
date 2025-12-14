# app/scanner.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from app.notifier import send_message


def scan_once() -> None:
    """
    클라우드(GitHub Actions) / 로컬(PyCharm) 공용 1회 스캔 함수

    현재 목적:
    - Actions가 실행되면 텔레그램으로 '무조건' 테스트 메시지 1회 전송
    - 이후 여기에 실제 종목 스캔 로직을 추가
    """

    # UTC / KST 시간 계산 (Actions는 UTC 환경)
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)

    # ===== 1️⃣ 무조건 보내는 테스트 메시지 =====
    send_message(
        "✅ [Stock Watcher] Cloud Scan 실행됨\n\n"
        f"🕒 UTC  : {now_utc.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🕘 KST  : {now_kst.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "이 메시지가 오면 GitHub Actions + Telegram 연동은 정상입니다."
    )

    # ===== 2️⃣ TODO: 실제 스캔 로직은 여기부터 추가 =====
    # 예시 구조:
    #
    # tickers = load_favorite_tickers()
    # for ticker in tickers:
    #     if check_conditions(ticker):
    #         send_message(f"📉 {ticker} 조건 충족")
    #
    # send_photo(chart_bytes, caption="차트 이미지")
    #
    # =====================================================
