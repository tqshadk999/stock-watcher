import pandas as pd
import yfinance as yf

# 안정적인 소스(테이블이 꾸준히 유지됨)
SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_WIKI = "https://en.wikipedia.org/wiki/Nasdaq-100"

def _normalize_symbol(sym: str) -> str:
    # yfinance 호환: BRK.B -> BRK-B
    return str(sym).strip().replace(".", "-")

def _load_sp500_symbols():
    # 첫 번째 테이블이 보통 "S&P 500 component stocks"
    tables = pd.read_html(SP500_WIKI)
    df = tables[0]
    # 컬럼명은 보통 'Symbol'
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    return [_normalize_symbol(s) for s in df[col].tolist()]

def _load_nasdaq100_symbols():
    # "Current components" 테이블 찾기 (Ticker 컬럼 포함)
    tables = pd.read_html(NASDAQ100_WIKI)
    target = None
    for t in tables:
        cols = {str(c).lower() for c in t.columns}
        if "ticker" in cols:
            target = t
            break
    if target is None:
        # fallback: 첫 테이블
        target = tables[0]

    # Ticker 컬럼 찾기
    ticker_col = None
    for c in target.columns:
        if str(c).lower() == "ticker":
            ticker_col = c
            break
    if ticker_col is None:
        ticker_col = target.columns[0]

    return [_normalize_symbol(s) for s in target[ticker_col].tolist()]

def load_universe(include_favorites=True, sanitize=True):
    sp500 = _load_sp500_symbols()
    ndx = _load_nasdaq100_symbols()

    symbols = set(sp500 + ndx)

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
                "market_cap": info.get("marketCap", 0),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)
