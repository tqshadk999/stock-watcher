import yfinance as yf
import pandas as pd

BB_WINDOW = 20
BB_STD = 2
VOLUME_WINDOW = 20
VOLUME_MULTIPLIER = 1.1


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


# 1️⃣ 볼린저밴드 하단 터치 후 반등
def cond_bb_rebound(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None:
        return False

    lower = _bollinger_lower(df)

    prev_low = df["Low"].iloc[-2]
    prev_close = df["Close"].iloc[-2]
    now_close = df["Close"].iloc[-1]

    return prev_low <= lower.iloc[-2] and now_close > prev_close


# 2️⃣ 반등 + 거래량 증가
def cond_bb_rebound_with_volume(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None:
        return False

    if not cond_bb_rebound(symbol):
        return False

    vol_now = df["Volume"].iloc[-1]
    vol_avg = df["Volume"].rolling(VOLUME_WINDOW).mean().iloc[-2]

    return vol_now >= vol_avg * VOLUME_MULTIPLIER


# 3️⃣ 반등 + 피보나치 되돌림
def cond_bb_rebound_with_fib(symbol: str) -> bool:
    df = _load_intraday(symbol)
    if df is None:
        return False

    if not cond_bb_rebound(symbol):
        return False

    recent = df.tail(50)
    low = recent["Low"].min()
    high = recent["High"].max()

    fib_618 = high - (high - low) * 0.618
    close_now = df["Close"].iloc[-1]

    return close_now <= fib_618


# =====================================================
# ✅ 🔧 핵심 해결부 (이게 없어서 터졌던 것)
# =====================================================

def scan_symbol(symbol: str) -> dict:
    """
    main.py가 요구하는 인터페이스용 래퍼
    기존 로직은 절대 변경하지 않음
    """
    return {
        "symbol": symbol,
        "bb_rebound": cond_bb_rebound(symbol),
        "bb_rebound_volume": cond_bb_rebound_with_volume(symbol),
        "bb_rebound_fib": cond_bb_rebound_with_fib(symbol),
    }
