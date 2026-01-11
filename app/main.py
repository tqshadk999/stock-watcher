from collections import defaultdict

from app.favorites import SECTOR_GROUPS, FAVORITES
from app.scanner import (
    cond_bb_rebound,
    cond_bb_rebound_with_volume,
    cond_bb_rebound_with_fib,
)
from app.telegram import send_message
from app.state import should_alert, mark_alerted


def run():
    condition_hits = {
        "1️⃣ BB 하단 터치 후 반등": [],
        "2️⃣ 반등 + 거래량 증가": [],
        "3️⃣ 반등 + 피보나치": [],
        "1️⃣+2️⃣": [],
        "1️⃣+3️⃣": [],
        "1️⃣+2️⃣+3️⃣": [],
    }

    # 섹터 → 심볼 목록 순회
    for sector, symbols in SECTOR_GROUPS.items():
        for symbol in symbols:
            if not should_alert(symbol):
                continue

            c1 = cond_bb_rebound(symbol)
            c2 = cond_bb_rebound_with_volume(symbol)
            c3 = cond_bb_rebound_with_fib(symbol)

            matched = []

            if c1:
                matched.append("1")
            if c2:
                matched.append("2")
            if c3:
                matched.append("3")

            if not matched:
                continue

            key = "1️⃣"
            if matched == ["1"]:
                key = "1️⃣ BB 하단 터치 후 반등"
            elif matched == ["1", "2"]:
                key = "1️⃣+2️⃣"
            elif matched == ["1", "3"]:
                key = "1️⃣+3️⃣"
            elif matched == ["1", "2", "3"]:
                key = "1️⃣+2️⃣+3️⃣"
            elif matched == ["2"]:
                key = "2️⃣ 반등 + 거래량 증가"
            elif matched == ["3"]:
                key = "3️⃣ 반등 + 피보나치"

            condition_hits[key].append(f"{symbol} ({sector})")
            mark_alerted(symbol)

    messages = []
    for title, items in condition_hits.items():
        if not items:
            continue
        msg = f"📌 {title}\n" + "\n".join(f"• {s}" for s in sorted(items))
        messages.append(msg)

    if messages:
        send_message("\n\n".join(messages))
    else:
        send_message("🔍 조건 충족 종목 없음")
