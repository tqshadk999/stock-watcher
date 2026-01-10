from app.sectors import FAVORITES

def load_universe(include_favorites=False):
    symbols = set(BASE_UNIVERSE)

    if include_favorites:
        symbols |= set(FAVORITES)

    return sorted(symbols)
