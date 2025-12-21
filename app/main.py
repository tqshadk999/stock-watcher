from collections import defaultdict
from app.universe import load_universe, attach_market_cap
from app.scanner import intraday_bb_rebound, intraday_bb_touch
from app.favorites import FAVORITES
from app.state import should_alert, mark_alerted
from app.formatter import format_sector_message, format_favorites
from app.telegram import send_message

def run():
    symbols = load_universe()
    df = attach_market_cap(symbols)

    sector_hits = defaultdict(list)
    favorite_hits = []

    for row in df.itertuples():
        symbol = row.symbol

        if not should_alert(symbol):
            continue

        # 즐겨찾기: BB 하단 터치만
        if symbol in FAVORITES:
            if intraday_bb_touch(symbol):
                favorite_hits.append(symbol)
                mark_alerted(symbol)
                continue

        # 일반 종목: 하단 터치 + 반등 + 거래량
        if intraday_bb_rebound(symbol):
            sector_hits[row.sector].append(symbol)
            mark_alerted(symbol)

    for sector, symbols in sector_hits.items():
        send_message(format_sector_message(sector, symbols))

    fav_msg = format_favorites(favorite_hits)
    if fav_msg:
        send_message(fav_msg)
