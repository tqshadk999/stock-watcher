import yfinance as yf
import pandas as pd

BB_WINDOW = 20
BB_STD = 2
VOLUME_WINDOW = 20
VOLUME_MULTIPLIER = 1.1
LOOKBACK_BARS = 78  # 프리 + 정규 + 애프터 커버


def _load_intraday(symbol: str):
    try:
        df = yf.download(
            symbol,
            period="7d",
            interval="5m",
            auto_adjust=True,
            progress=False,
        )
        if df.empty or len(df) < BB_WINDOW + 2:
            return None
        return df
    except Exception:
        return None


def _bollinger_lower(df: pd.DataFrame):
    ma = df["Close"].rolling(BB_WINDOW).mean()
    std = df["Close"].rolling(BB_WINDOW).std()
    return ma - BB_STD * std


# ① 하단 터치 이력
def cond_touch(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None:
        return False

    df = df.tail(LOOKBACK_BARS)
    lower = _bollinger_lower(df)
    return (df["Low"] <= lower).any()


# ② 터치 후 반등
def cond_rebound(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None:
        return False

    lower = _bollinger_lower(df)

    prev_low = df["Low"].iloc[-2]
    prev_close = df["Close"].iloc[-2]
    now_close = df["Close"].iloc[-1]

    return prev_low <= lower.iloc[-2] and now_close > prev_close


# ③ 반등 + 거래량
def cond_rebound_volume(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None or not cond_rebound(symbol):
        return False

    vol_now = float(df["Volume"].iloc[-1])
    vol_avg = float(df["Volume"].rolling(VOLUME_WINDOW).mean().iloc[-2])

    return vol_now >= vol_avg * VOLUME_MULTIPLIER


# ④ 반등 + 피보나치
def cond_rebound_fib(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None or not cond_rebound(symbol):
        return False

    recent = df.tail(50)
    low = float(recent["Low"].min())
    high = float(recent["High"].max())

    fib_618 = high - (high - low) * 0.618
    close_now = float(df["Close"].iloc[-1])

    return close_now <= fib_618


# ✅ 조건 레지스트리 (🔥 여기만 수정하면 조건 추가됨)
CONDITIONS = {
    "T": cond_touch,
    "R": cond_rebound,
    "V": cond_rebound_volume,
    "F": cond_rebound_fib,
}
