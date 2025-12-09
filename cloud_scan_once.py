# app/cloud_scan_once.py
"""
GitHub Actions에서 실행할 '단발성 스캐너'

- 오늘 기준 한 번 S&P500 + NASDAQ100 전체를 스캔
- 조건에 맞는 종목이 있으면 텔레그램으로 차트 전송
- 실행 시작/종료 시점에도 무조건 텔레그램 메시지 전송
"""

import os
from datetime import datetime

import pandas as pd

from notifier import send_message, send_photo
from utils import (
    get_sp500_tickers,
    get_nasdaq100_tickers,
    safe_download_symbol,
    add_indicators,
    evaluate_conditions,
)

# main.py 의 차트 함수 재사용
from main import build_chart

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def make_caption(index_name: str, symbol: str, df: pd.DataFrame, conds: dict, now: datetime) -> str:
    """알림용 텍스트 캡션 생성 (시가/고가/저가/종가 포함)"""
    last = df.iloc[-1]
    o = float(last.get("Open", float("nan")))
    h = float(last.get("High", float("nan")))
    l = float(last.get("Low", float("nan")))
    c = float(last.get("Close", float("nan")))

    lines = [f"*{index_name} / {symbol}*"]

    if conds.get("bollinger_rebound"):
        lines.append("• 볼린저 밴드 하단 터치 후 반등")
    if conds.get("breakout_90d"):
        lines.append("• 최근 90일 신고가 돌파")
    if conds.get("mfi_strong"):
        lines.append("• MFI 강세 (50 이상)")
    if conds.get("volume_strong"):
        lines.append("• 거래량 20MA 상회")

    lines.append("")
    lines.append(f"시가: {o:,.2f}")
    lines.append(f"고가: {h:,.2f}")
    lines.append(f"저가: {l:,.2f}")
    lines.append(f"종가: {c:,.2f}")
    lines.append(f"\n시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def run_once():
    """S&P500 + NASDAQ100 전체를 한 번만 검사"""

    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("환경 변수 TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다.")

    now = datetime.now()

    # 🔔 1) 실행 시작 알림 (항상 발송)
    send_message(
        TELEGRAM_TOKEN,
        CHAT_ID,
        f"☁️ GitHub Actions 스캐너 실행 시작\n시간: {now.strftime('%Y-%m-%d %H:%M:%S')}",
    )

    indices = {
        "S&P500": get_sp500_tickers(),
        "NASDAQ100": get_nasdaq100_tickers(),
    }

    total_checked = 0
    total_matched = 0

    for index_name, tickers in indices.items():
        for symbol in tickers:
            total_checked += 1
            try:
                # 일봉 기준 최근 120일 (조건 + 차트용)
                df = safe_download_symbol(symbol, period="120d", interval="1d")
                if df is None or df.empty:
                    continue

                df = add_indicators(df)
                conds = evaluate_conditions(df)
                if not conds.get("trigger", False):
                    continue

                total_matched += 1

                caption = make_caption(index_name, symbol, df, conds, now)

                try:
                    chart_bytes = build_chart(df, symbol, index_name, conds)
                    send_photo(TELEGRAM_TOKEN, CHAT_ID, chart_bytes, caption=caption, parse_mode="Markdown")
                except Exception as e:
                    # 차트 생성 실패 시 텍스트만 전송
                    send_message(
                        TELEGRAM_TOKEN,
                        CHAT_ID,
                        caption + f"\n\n(차트 생성 중 오류 발생: {e})",
                    )

            except Exception:
                # 개별 종목 에러는 무시하고 다음 종목으로 진행
                continue

    # 🔔 2) 실행 종료 알림 (항상 발송)
    end_time = datetime.now()
    duration_sec = int((end_time - now).total_seconds())

    summary = (
        "☁️ GitHub Actions 스캐너 실행 종료\n"
        f"기간: {now.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"소요 시간: {duration_sec}초\n"
        f"검사 종목 수: {total_checked}개\n"
        f"조건 일치 종목 수: {total_matched}개"
    )

    send_message(TELEGRAM_TOKEN, CHAT_ID, summary)


if __name__ == "__main__":
    run_once()
