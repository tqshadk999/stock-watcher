import pandas as pd
import numpy as np

BOLL_WINDOW = 20
BOLL_STD = 2
VOLUME_WINDOW = 20
FIB_WINDOW = 60


def scan_symbol(df: pd.DataFrame):
    """
    return: set of triggered condition numbers {1,2,3}
    """

    triggered = set()

    if len(df) < max(BOLL_WINDOW, VOLUME_WINDOW, FIB_WINDOW) + 2:
        return triggered

    close = df["Close"]
    low = df["Low"]
    volume = df["Volume"]

    # === Bollinger Bands ===
    ma = close.rolling(BOLL_WINDOW).mean()
    std = close.rolling(BOLL_WINDOW).std()
    lower = ma - BOLL_STD * std

    close_now = close.iloc[-1].item()
    close_prev = close.iloc[-2].item()
    lower_prev = lower.iloc[-2].item()

    # 1️⃣ 볼린저 하단 터치 후 반등
    cond1 = close_prev <= lower_prev and close_now > close_prev
    if cond1:
        triggered.add(1)

    # === Volume ===
    vol_now = volume.iloc[-1].item()
    vol_avg = volume.rolling(VOLUME_WINDOW).mean().iloc[-2].item()

    # 2️⃣ 조건1 + 거래량 평균 돌파
    cond2 = cond1 and vol_now > vol_avg
    if cond2:
        triggered.add(2)

    # === Fibonacci ===
    recent = df.iloc[-FIB_WINDOW:]
    low_recent = recent["Low"].min().item()
    high_recent = recent["High"].max().item()

    fib_382 = high_recent - (high_recent - low_recent) * 0.382
    fib_618 = high_recent - (high_recent - low_recent) * 0.618

    # 3️⃣ 조건1 + 피보나치 구간
    cond3 = cond1 and fib_618 <= close_now <= fib_382
    if cond3:
