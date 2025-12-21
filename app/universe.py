import pandas as pd
import os
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

SP500_FILE = os.path.join(DATA_DIR, "sp500.csv")
NASDAQ100_FILE = os.path.join(DATA_DIR, "nasdaq100.csv")

def _normalize_symbol(sym: str) -> str:
    return str(sym).strip().replace(".", "-")

def _load_csv_symbols(path):
    df = pd.read_csv(path)
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    return [_normalize_symbol(s) for s in df[col].tolist()]

def load_universe(include_favorites=True, sanitize=True):
    symbols = set()

    # S&P500
    symbols.update(_load_csv_symbols(SP500_FILE))

    # Nasdaq100
    symbols.update(_load_csv_symbols(NASDAQ100_FILE))

    # Favorites 강제 포함
    if include_favorites:
        from app.favorites import FAVORITES
        symbols.update(_normalize_symbol(s) for s in FAVORITES)

    symbols = sorted(symbols)

    # yfinance 조회 불가 티커 제거
    if sanitize:
        from app.ticker_sanitize import sanitize_symbols
        symbols, _ = sanitize_symbols(symbols)

    return symbols

def attach_market_cap(symbols):
    rows = []
    for s in symbols:
        try:
            info = yf.Ticker(s).info
            rows.append({
                "symbol": s,
                "sector": info.get("sector", "Unknown"),
                "market_cap": info.get("marketCap", 0),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)
