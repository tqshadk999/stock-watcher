# app/main.py
import os
import time
import logging
from datetime import datetime

from app.notifier import send_message, send_photo
from app.utils import (
    get_sp500_tickers,
    get_nasdaq100_tickers,
    safe_download_symbol,
    add_indicators,
    evaluate_conditions,
    top_n_by_marketcap,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [scanner] %(message)s")

# PyCharm/로컬에서 쓰던 설정값들(필요시 유지)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "30"))
TOPN = int(os.getenv("TOPN", "10"))
TOPN_TIMES = ["08:00", "12:00", "22:00"]  # 요청하신 시간 기준

sp500_tickers: list[str] = []
nasdaq_tickers: list[str] = []
combined: list[tuple[str, str]] = []  # (index_name, symbol)

last_alert_time: dict[tuple[str, str], datetime] = {}
last_topn_sent: dict[tuple[str, str], datetime.date] = {}


def init_tickers():
    global sp500_tickers, nasdaq_tickers, combined
    sp500_tickers = get_sp500_tickers()
    nasdaq_tickers = get_nasdaq100_tickers()
    combined = [("S&P500", s) for s in sp500_tickers] + [("NASDAQ100", s) for s in nasdaq_tickers]
    logger.info(f"Loaded {len(sp500_tickers)} S&P500, {len(nasdaq_tickers)} NASDAQ100 tickers")


def check_symbol_and_alert(index_name: str, symbol: str, now: datetime):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다.")

    try:
        df = safe_download_symbol(symbol, period="120d", interval="1d")  # ✅ 일봉
        if df is None or df.empty:
            return

        df = add_indicators(df)
        conds = evaluate_conditions(df)
        if not conds.get("trigger"):
            return

        key = (index_name, symbol)
        last_time = last_alert_time.get(key)
        if last_time and (now - last_time).total_seconds() < 7200:
            return

        # 메시지
        text_lines = [f"*{index_name} / {symbol}*"]
        if conds.get("bollinger_rebound"):
            text_lines.append("• 볼린저 밴드 하단 터치 후 반등")
        if conds.get("breakout_90d"):
            text_lines.append("• 최근 90일 신고가 돌파")
        if conds.get("mfi_strong"):
            text_lines.append("• MFI 강세 (50 이상)")
        if conds.get("volume_strong"):
            text_lines.append("• 거래량 20MA 상회")
        text_lines.append(f"\n시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        caption = "\n".join(text_lines)

        # 차트(기존 build_chart를 utils나 다른 파일에 두셨다면 그대로 호출)
        # 여기서는 df로 차트 생성하는 함수를 이미 갖고 있다고 가정합니다.
        chart_bytes = conds["chart_bytes"] if "chart_bytes" in conds else None
        if chart_bytes:
            send_photo(token, chat_id, chart_bytes, caption=caption, parse_mode="Markdown")
        else:
            send_message(token, chat_id, caption)

        last_alert_time[key] = now
        time.sleep(0.5)

    except Exception as e:
        logger.warning(f"Error processing {index_name} {symbol}: {e}")


def run_cloud_once(now: datetime | None = None):
    """✅ GitHub Actions용: 무조건 1회만 스캔하고 종료"""
    if now is None:
        now = datetime.now()

    init_tickers()

    # 여기서도 “조건 만족 종목이 하나도 없을 때”를 대비해 실행 로그용 메시지를 원하면 추가 가능
    matched_count = 0
    for index_name, symbol in combined:
        before = matched_count
        check_symbol_and_alert(index_name, symbol, now)
        # check_symbol_and_alert에서 실제로 보냈는지 판단하려면 반환값 처리하도록 바꿀 수 있음

    logger.info("Cloud scan finished (single pass).")


# (로컬 24/7용 루프는 원하면 유지)
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다.")

    init_tickers()
    logger.info("=== 24/7 stock watcher started ===")

    cursor = 0
    while True:
        now = datetime.now()
        # 배치 스캔(로컬용)
        if combined:
            start = cursor
            end = min(cursor + BATCH_SIZE, len(combined))
            batch = combined[start:end]
            cursor = 0 if end >= len(combined) else end

            for index_name, symbol in batch:
                check_symbol_and_alert(index_name, symbol, now)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
