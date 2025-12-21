import yfinance as yf

def _load_intraday(symbol):
    df = yf.download(symbol, period="1d", interval="5m", progress=False)
    if df is None or len(df) < 30:
        return None
    return df

def _volume_increased(symbol, threshold=1.1):
    daily = yf.download(symbol, period="2d", interval="1d", progress=False)
    if daily is None or len(daily) < 2:
        return False
    return daily["Volume"].iloc[-1] >= daily["Volume"].iloc[-2] * threshold

def intraday_bb_rebound(symbol, rebound_window=3):
    if not _volume_increased(symbol):
        return False

    df = _load_intraday(symbol)
    if df is None:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std = close.rolling(20).std()
    bb_lower = ma20 - 2 * std

    for idx in df.index[df["Low"] < bb_lower]:
        pos = df.index.get_loc(idx)
        window = df.iloc[pos+1:pos+1+rebound_window]
        if (window["Close"] > window["Open"]).any():
            return True

    return False

def intraday_bb_touch(symbol):
    df = _load_intraday(symbol)
    if df is None:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std = close.rolling(20).std()
    bb_lower = ma20 - 2 * std

    return (df["Low"] < bb_lower).any()
