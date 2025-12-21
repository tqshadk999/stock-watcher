import pandas as pd
import yfinance as yf

SP500_URL = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
NASDAQ100_URL = "https://datahub.io/core/nasdaq-100/r/constituents.csv"

def _normalize_symbol(sym: str) -> str:
    # yfinance는 점(.) 대신 대시(-)를 쓰는 경우가 많음 (예: BRK.B -> BRK-B)
    return sym.replace(".", "-").strip()

def load_universe(include_favorites=True):
    # S&P500
    sp500 = pd.read_csv(SP500_URL)
    sp500_symbols = [_normalize_symbol(s) for s in sp500["Symbol"].tolist()]

    # Nasdaq100
    ndx = pd.read_csv(NASDAQ100_URL)
    # 데이터허브 파일에서 컬럼명이 Symbol인 경우가 대부분
    col = "Symbol" if "Symbol" in ndx.columns else ndx.columns[0]
    ndx_symbols = [_normalize_symbol(s) for s in ndx[col].tolist()]

    symbols = set(sp500_symbols + ndx_symbols)

    if include_favorites:
        from app.favorites import FAVORITES
        symbols.update(_normalize_symbol(s) for s in FAVORITES)

    return sorted(symbols)

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
        except:
            continue
    return pd.DataFrame(rows)
