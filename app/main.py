from app.universe import load_universe
from app.scanner import (
    condition_1_bb_rebound,
    condition_2_bb_rebound_volume,
    condition_3_bb_fibonacci
)
from app.formatter import format_message
from app.telegram import send_message
from app.state import should_alert, mark_alerted

def run():
    universe = load_universe()

    for item in universe:
        symbol = item["symbol"]
        sector = item["sector"]

        if not should_alert(symbol):
            continue

        conditions = []

        if condition_1_bb_rebound(symbol):
            conditions.append("C1")
        if condition_2_bb_rebound_volume(symbol):
            conditions.append("C2")
        if condition_3_bb_fibonacci(symbol):
            conditions.append("C3")

        if conditions:
            msg = format_message(symbol, sector, conditions)
            send_message(msg)
            mark_alerted(symbol)
