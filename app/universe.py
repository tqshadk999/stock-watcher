import pandas as pd
from pathlib import Path


DATA_DIR = Path("data")


def load_universe(include_favorites=True, sanitize=True):
    universe = {}

    # S&P500
    sp500 = pd.read_csv(DATA_DIR / "sp500.csv")
    for _, r in sp500.iterrows():
        universe[r["Symbol"]] = {"sector": r.get("Sector", "SP500")}

    # Nasdaq100
    nasdaq = pd.read_csv(DATA_DIR / "nasdaq100.csv")
    for _, r in nasdaq.iterrows():
        universe[r["Symbol"]] = {"sector": r.get("Sector", "Nasdaq100")}

    # Favorites (선택)
    if include_favorites:
        favorites = {
            "AAPL": "Tech",
            "MSFT": "Tech",
            "NVDA": "AI",
            "TSLA": "Auto",
        }
        for k, v in favorites.items():
            universe[k] = {"sector": v}

    return universe
