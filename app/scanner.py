import yfinance as yf
import pandas as pd
import numpy as np

BB_WINDOW = 20
BB_STD = 2
VOLUME_WINDOW = 20


def _get_intraday_df(symbol, period="5d", interval="5m"):
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
        threads=False
    )

    if df is None or df.empty or len(df) < BB_WINDOW + 2:
        return None

    return df


def _bollinger(df):
    ma = df["Close"].rolling(BB_WINDOW).mean()
    std = df["Close"].rolling(BB_WINDOW).std()
    lower = ma - BB_STD * std
    return ma, lower


# 1️⃣ 볼린저 하단 터치 후 반등
def condition_1_bb_rebound(symbol):
    df = _get_intraday_df(symbol)
    if df is None:
        return False

    ma, lower = _bollinger(df)

    low_prev = float(df["Low"].iloc[-2])
    close_prev = float(df["Close"].iloc[-2])
    close_now = float(df["Close"].iloc[-1])
    lower_prev = float(lower.iloc[-2])

    return low_prev <= lower_prev and close_now > close_prev


# 2️⃣ 볼린저 하단 반등 + 거래량 평균 돌파
def condition_2_bb_rebound_volume(symbol):
    df = _get_intraday_df(symbol)
    if df is None:
        return False

    ma, lower = _bollinger(df)

    low_prev = float(df["Low"].iloc[-2])
    close_prev = float(df["Close"].iloc[-2])
    close_now = float(df["Close"].iloc[-1])
    lower_prev = float(lower.iloc[-2])

    vol_now = float(df["Volume"].iloc[-1])
    vol_avg = float(df["Volume"].rolling(VOLUME_WINDOW).mean().iloc[-2])

    return (
        low_prev <= lower_prev
        and close_now > close_prev
        and vol_now >= vol_avg * 1.1
    )


# 3️⃣ 볼린저 하단 터치 + 피보나치 되돌림
def condition_3_bb_fibonacci(symbol):
    df = _get_intraday_df(symbol)
    if df is None:
        return False

    recent = df.tail(50)

    low = float(recent["Low"].min())
    high = float(recent["High"].max())

    fib_382 = high - (high - low) * 0.382
    fib_618 = high - (high - low) * 0.618

    close_now = float(df["Close"].iloc[-1])
    low_prev = float(df["Low"].iloc[-2])

    return low_prev <= fib_618 and fib_618 <= close_now <= fib_382
