# app/main.py
import os
from datetime import datetime
from scanner import load_price, add_indicators, check_conditions
from notifier import bot
from utils import get_sp500_tickers, get_nasdaq100_tickers

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

favorites = ["AAPL", "TSLA", "NVDA", "MSFT"]  # 즐겨찾기 종목

combined = []


def init_tickers():
    """전체 티커 불러와 combined 배열 구성"""
    global combined
    combined = []
    sp500 = get_sp500_tickers()
    nasdaq = get_nasdaq100_tickers()

    for t in sp500:
        combined.append(("S&P500", t))
    for t in nasdaq:
        combined.append(("NASDAQ100", t))
    for t in favorites:
        combined.append(("FAVORITE", t))


def check_symbol_and_alert(index_name, symbol, now):
    df = load_price(symbol)
    if df is None or len(df) < 20:
        return

    df = add_indicators(df)
    if df is None:
        return

    if check_conditions(df):
        last_price = df["Close"].iloc[-1]
        msg = (
            f"📈 조건 충족\n"
            f"- 지수: {index_name}\n"
            f"- 종목: {symbol}\n"
            f"- 가격: {last_price:.2f}\n"
        )
        bot.send_message(chat_id=CHAT_ID, text=msg)


if __name__ == "__main__":
    # PC에서 실행될 때만 돌아감 (GitHub Actions와 구분)
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("환경변수 TELEGRAM_TOKEN 또는 CHAT_ID가 없습니다.")

    init_tickers()
    bot.send_message(chat_id=CHAT_ID, text="💻 로컬 PC 스캐너 실행됨 (main.py)")

    now = datetime.now()
    for index_name, symbol in combined:
        check_symbol_and_alert(index_name, symbol, now)
