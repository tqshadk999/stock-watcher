import yfinance as yf
import re

_cache = {}

REMOVE = [
    r"\bInc\.?\b", r"\bCorp\.?\b", r"\bCorporation\b",
    r"\bLtd\.?\b", r"\bHoldings?\b", r"\bClass\s[A-Z]\b"
]

def get_company_name(symbol):
    if symbol in _cache:
        return _cache[symbol]

    info = yf.Ticker(symbol).info
    name = info.get("shortName") or symbol
    for r in REMOVE:
        name = re.sub(r, "", name, flags=re.I)
    name = re.sub(r"\s{2,}", " ", name).strip()

    _cache[symbol] = name
    return name
