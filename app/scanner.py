# scanner.py

import matplotlib.pyplot as plt
from telegram import Bot
from io import BytesIO

from utils import (
    get_sp500_tickers,
    get_nasdaq100_tickers,
    load_price,
    add_indicators,
    check_conditions,
)
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ALERT_TIMES

bot = Bot(token=TELEGRAM_TOKEN)


# ───────────────────────────────────────────────────────────────
# 텔레그램 발송 함수
# ───────────────────────────────────────────────────────────────
def send_chart(df, symbol, index_name, condition_text):
    plt.figure(figsize=(12, 8))

    # 가격 + 볼린저밴드
    plt.plot(df["Close"], label="Close")
    plt.plot(df["MA5"], label="MA5")
    plt.plot(df["MA20"], label="MA20")
    plt.plot(df["MA60"], label="MA60")
    plt.plot(df["MA120"], label="MA120")

    plt.plot(df["BB_UPPER"], label="Upper BB")
    plt.plot(df["BB_LOWER"], label="Lower BB")

    # 신고가 돌파 영역
    df["90D_HIGH"].plot(label="90D High", linestyle="--")

    plt.title(f"{index_name} / {symbol} / {condition_text}")
    plt.legend()

    img = BytesIO()
    plt.savefig(img, format="png", dpi=200)
    img.seek(0)
    plt.close()

    bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=img)


# ───────────────────────────────────────────────────────────────
# 즉시 조건 스캔 → 텔레그램 발송
# ───────────────────────────────────────────────────────────────
def scan_now():
    for index_name, loader in {
        "S&P500": get_sp500_tickers,
        "NASDAQ100": get_nasdaq100_tickers,
    }.items():

        tickers = loader()
        for t in tickers:
            df = load_price(t)
            if df is None:
                continue

            df = add_indicators(df)
            if len(df) < 120:
                continue

            if check_conditions(df):
                last = df.iloc[-1]
                cond_text = "조건 충족"

                send_chart(df, t, index_name, cond_text)
                bot.send_message(
                    text=f"📌 {index_name} / {t}\n조건 충족: 볼린저 반등 / 신고가 / MFI / 거래량",
                    chat_id=TELEGRAM_CHAT_ID,
                )

    print("조건 스캔 완료")


# ───────────────────────────────────────────────────────────────
# 예약 시간 추천 종목(시총순 Top10) 발송
# ───────────────────────────────────────────────────────────────
def send_top10():
    for index_name, loader in {
        "S&P500": get_sp500_tickers,
        "NASDAQ100": get_nasdaq100_tickers,
    }.items():
        tickers = loader()
        selected = []

        for t in tickers:
            df = load_price(t)
            if df is None:
                continue

            df = add_indicators(df)
            if len(df) < 120:
                continue

            if check_conditions(df):
                selected.append((t, df["Close"].iloc[-1]))

        selected = sorted(selected, key=lambda x: x[1], reverse=True)[:10]
        msg = "🔥 " + index_name + " 추천 Top10\n" + "\n".join([x[0] for x in selected])

        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)


