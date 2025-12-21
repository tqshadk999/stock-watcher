import pandas as pd
import yfinance as yf

SP500_URL = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
NASDAQ100_URL = "https://datahub.io/core/nasdaq-100/r/constituents.csv"

def _normalize_symbol(sym: str) -> str:
    return sym.replace(".", "-").strip()

def load_universe(include_favorites=True, sanitize=True):
    sp500 = pd.read_csv(SP500_URL)
    sp500_symbols = [_normalize_symbol(s) for s in sp500["Symbol"].tolist()]

    ndx = pd.read_csv(NASDAQ100_URL)
    col = "Symbol" if "Symbol" in ndx.columns else ndx.columns[0]
    ndx_symbols = [_normalize_symbol(s) for s in ndx[col].tolist()]

    symbols = set(sp500_symbols + ndx_symbols)

    if include_favorites:
        from app.favorites import FAVORITES
        symbols.update(_normalize_symbol(s) for s in FAVORITES)

    symbols = sorted(symbols)

    if sanitize:
        from app.ticker_sanitize import sanitize_symbols
        symbols, _dropped = sanitize_symbols(symbols)

    return symbols


def attach_market_cap(symbols):
    rows = []
    for s in symbols:
        try:
            info = yf.Ticker(s).info
            rows.append({
                "symbol": s,
                "sector": info.get("sector", "Unknown"),
                "market_cap": info.get("marketCap", 0)
            })
        except Exception:
            continue
    return pd.DataFrame(rows)
