import yfinance as yf
import pandas as pd
import numpy as np

def _load(symbol, period="5d", interval="15m"):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 30:
        return None
    return df

def _bollinger(df, window=20):
    ma = df["Close"].rolling(window).mean()
    std = df["Close"].rolling(window).std()
    lower = ma - 2 * std
    return lower

def condition_1_bb_rebound(symbol):
    df = _load(symbol)
    if df is None:
        return False

    lower = _bollinger(df)
    return df["Low"].iloc[-2] <= lower.iloc[-2] and df["Close"].iloc[-1] > df["Close"].iloc[-2]

def condition_2_bb_rebound_volume(symbol):
    df = _load(symbol)
    if df is None:
        return False

    lower = _bollinger(df)
    vol_avg = df["Volume"].rolling(20).mean()

    return (
        df["Low"].iloc[-2] <= lower.iloc[-2]
        and df["Close"].iloc[-1] > df["Close"].iloc[-2]
        and df["Volume"].iloc[-1] >= vol_avg.iloc[-1] * 1.1
    )

def condition_3_bb_fibonacci(symbol):
    df = _load(symbol)
    if df is None:
        return False

    low = df["Low"].min()
    high = df["High"].max()
    fib_382 = high - (high - low) * 0.382
    price = df["Close"].iloc[-1]

    return abs(price - fib_382) / fib_382 < 0.01
