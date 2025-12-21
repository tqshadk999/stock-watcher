import yfinance as yf
import pandas as pd


# ===============================
# 공통: 장중 5분봉 로드
# ===============================
def _load_intraday(symbol):
    df = yf.download(
        symbol,
        period="1d",
        interval="5m",
        progress=False
    )
    if df is None or len(df) < 30:
        return None
    return df


# ===============================
# 전일 대비 거래량 조건
# ===============================
def _volume_increased(symbol, threshold=1.1):
    """
    오늘 누적 거래량 >= 전일 거래량 * threshold
    """
    try:
        daily = yf.download(
            symbol,
            period="2d",
            interval="1d",
            progress=False
        )
        if daily is None or len(daily) < 2:
            return False

        yesterday_vol = daily["Volume"].iloc[-2]
        today_vol = daily["Volume"].iloc[-1]

        if yesterday_vol == 0:
            return False

        return today_vol >= yesterday_vol * threshold
    except:
        return False


# ===============================
# 일반 종목: BB 하단 터치 + 반등 이력 + 거래량 증가
# ===============================
def intraday_bb_rebound(
    symbol,
    rebound_window=3,
    volume_threshold=1.1
):
    # 거래량 먼저 컷 (부하 감소)
    if not _volume_increased(symbol, volume_threshold):
        return False

    df = _load_intraday(symbol)
    if df is None:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std = close.rolling(20).std()
    bb_lower = ma20 - 2 * std

    touch_indices = df.index[df["Low"] < bb_lower]

    for idx in touch_indices:
        pos = df.index.get_loc(idx)
        window = df.iloc[pos + 1 : pos + 1 + rebound_window]

        if len(window) == 0:
            continue

        rebound = (
            (window["Close"] > window["Open"]).any()
            or (window["Low"] > df.iloc[pos]["Low"]).any()
        )

        if rebound:
            return True

    return False


# ===============================
# 즐겨찾기: BB 하단 터치만 (거래량 조건 ❌)
# ===============================
def intraday_bb_touch(symbol):
    df = _load_intraday(symbol)
    if df is None:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std = close.rolling(20).std()
    bb_lower = ma20 - 2 * std

    return bool((df["Low"] < bb_lower).any())

