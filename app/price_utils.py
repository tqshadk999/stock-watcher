import yfinance as yf

_cache = {}

def get_change_pct(symbol):
    if symbol in _cache:
        return _cache[symbol]

    df = yf.download(symbol, period="2d", interval="1d", progress=False)
    if len(df) < 2:
        return None

    pct = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
    _cache[symbol] = pct
    return pct
