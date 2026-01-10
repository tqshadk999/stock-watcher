from app.favorites import SECTOR_GROUPS

def load_universe():
    """
    즐겨찾기 종목만으로 Universe 구성
    """
    universe = []

    for sector, symbols in SECTOR_GROUPS.items():
        for symbol in symbols:
            universe.append({
                "symbol": symbol,
                "sector": sector
            })

    return universe
