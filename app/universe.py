import pandas as pd
import yfinance as yf

SP500_URL = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"

NASDAQ100 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","AMD",
    "COST","PEP","NFLX","CSCO","INTC","QCOM","ADBE","TXN","AMAT","INTU"
]

def load_universe():
    sp500 = pd.read_csv(SP500_URL)
    return sorted(set(sp500["Symbol"].tolist() + NASDAQ100))

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
