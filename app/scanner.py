import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# 공통 설정
# =========================

PERIOD = "5d"
INTERVAL = "5m"

BB_WINDOW = 20
BB_STD = 2

VOLUME_WINDOW = 20
VOLUME_MULTIPLIER = 1.1

FIB_LOOKBACK = 50


# =========================
# 데이터 로드
# =========================

def load_intraday(symbol: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=PERIOD,
        interval=INTERVAL,
        progress=False,
        auto_adjust=True,
    )

    if df is None or df.empty or len(df) < BB_WINDOW + 5:
        return None

    return df


# =========================
# 볼린저 밴드 계산
# =========================

def bollinger_bands(close: pd.Series):
    ma = close.rolling(BB_WINDOW).mean()
    std = close.rolling(BB_WINDOW).std()
    upper = ma + BB_STD * std
    lower = ma - BB_STD * std
    return upper, lower


# =========================
# 1️⃣ BB 하단 터치 후 반등
# =========================

def condition_1_bb_rebound(symbol: str) -> bool:
    df = load_intraday(symbol)
    if df is None:
        return False

    upper, lower = bollinger_bands(df["Close"])

    low_prev = float(df["Low"].iloc[-2])
    close_prev = float(df["Close"].iloc[-2])
    close_now = float(df["Close"].iloc[-1])
    lower_prev = float(lower.iloc[-2])

    return low_prev <= lower_prev and close_now > close_prev


# =========================
# 2️⃣ BB 반등 + 거래량 증가
# =========================

def condition_2_bb_rebound_with_volume(symbol: str) -> bool:
    df = load_intraday(symbol)
    if df is None:
        return False

    upper, lower = bollinger_bands(df["Close"])

    low_prev = float(df["Low"].iloc[-2])
    close_prev = float(df["Close"].iloc[-2])
    close_now = float(df["Close"].iloc[-1])
    lower_prev = float(lower.iloc[-2])

    vol_now = float(df["Volume"].iloc[-1])
    vol_avg = float(df["Volume"].rolling(VOLUME_WINDOW).mean().iloc[-2])

    return (
        low_prev <= lower_prev
        and close_now > close_prev
        and vol_now >= vol_avg * VOLUME_MULTIPLIER
    )


# =========================
# 3️⃣ BB + 피보나치 되돌림
# =========================

def condition_3_bb_fibonacci(symbol: str) -> bool:
    df = load_intraday(symbol)
    if df is None:
        return False

    recent = df.tail(FIB_LOOKBACK)
    low = float(recent["Low"].min())
    high = float(recent["High"].max())

    if high <= low:
        return False

    fib_382 = high - (high - low) * 0.382
    fib_618 = high - (high - low) * 0.618

    close_now = float(df["Close"].iloc[-1])
    low_prev = float(df["Low"].iloc[-2])

    return fib_618 <= close_now <= fib_382 and low_prev <= fib_618
