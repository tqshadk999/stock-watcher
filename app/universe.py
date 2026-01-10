# app/universe.py
from app.favorites import FAVORITES

BASE_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL"
]

def load_universe(include_favorites: bool = True):
    symbols = set(BASE_UNIVERSE)

    if include_favorites:
        symbols |= set(FAVORITES)

    return sorted(symbols)
