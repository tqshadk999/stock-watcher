from collections import defaultdict

from app.universe import load_universe, attach_market_cap
from app.scanner import (
    cond_bb_rebound,
    cond_bb_rebound_with_volume,
    cond_bb_rebound_with_fib,
)
from app.favorites import FAVORITES
from app.state import should_alert, mark_alerted
from app.formatter import format_sector_block, format_favorites_block
from app.telegram import send_message

TOP_PER_SECTOR = 10


def run():
    symbols = load_universe(include_favorites=True)
    df = attach_market_cap(symbols)

    sector_hits = defaultdict(list)
    favorite_hits = []

    for row in df.itertuples():
        symbol = row.symbol
        sector = row.sector or "ETC"

        if not should_alert(symbol):
            continue

        conds = []

        if cond_bb_rebound(symbol):
            conds.append("1")
        if cond_bb_rebound_with_volume(symbol):
            conds.append("2")
        if cond_bb_rebound_with_fib(symbol):
            conds.append("3")

        if not conds:
            continue

        if symbol in FAVORITES:
            favorite_hits.append((symbol, conds))
        else:
            sector_hits[sector].append(
                (symbol, row.market_cap or 0, conds)
            )

        mark_alerted(symbol)

    messages = []

    for sector, items in sector_hits.items():
        items.sort(key=lambda x: x[1], reverse=True)
        messages.append(
            format_sector_block(sector, items[:TOP_PER_SECTOR])
        )

    if favorite_hits:
        messages.append(format_favorites_block(favorite_hits))

    if messages:
        send_message("\n\n".join(messages))
