# app/universe.py

from app.favorites import FAVORITES

BASE_UNIVERSE = [
    "AAPL",  # 시스템 테스트용
    "MSFT",
    "GOOGL",
]

def load_universe(include_favorites=True):
    symbols = set(BASE_UNIVERSE)

    if include_favorites:
        symbols.update(FAVORITES)

    return sorted(symbols)
