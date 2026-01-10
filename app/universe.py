import pandas as pd


def load_universe(include_favorites=False):
    sp500 = pd.read_csv("data/sp500.csv")["Symbol"].tolist()
    nasdaq = pd.read_csv("data/nasdaq100.csv")["Symbol"].tolist()

    symbols = set(sp500 + nasdaq)

    if include_favorites:
        from app.favorites import FAVORITES
        symbols.update(FAVORITES)

    return sorted(symbols)


def attach_market_cap(symbols):
    import yfinance as yf

    rows = []

    for s in symbols:
        try:
            info = yf.Ticker(s).info
            rows.append({
                "symbol": s,
                "sector": info.get("sector"),
                "market_cap": info.get("marketCap", 0),
            })
        except Exception:
            continue

    return pd.DataFrame(rows)
