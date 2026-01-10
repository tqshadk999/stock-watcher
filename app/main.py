from collections import defaultdict
from datetime import datetime

from app.universe import load_universe
from app.scanner import (
    condition_1_bb_rebound,
    condition_2_bb_rebound_with_volume,
    condition_3_bb_fibonacci,
)
from app.favorites import SECTOR_GROUPS, FAVORITES
from app.telegram import send_message


# =========================
# 설정
# =========================

MAX_PER_SECTOR = 10
TIMEZONE = "KST"


# =========================
# Helper: 심볼 → 섹터 찾기
# =========================

def get_sector(symbol: str) -> str:
    for sector, symbols in SECTOR_GROUPS.items():
        if symbol in symbols:
            return sector
    return "UNCLASSIFIED"


# =========================
# 메인 실행 함수
# =========================

def run():
    symbols = load_universe(include_favorites=True)

    hits = {
        "C1": defaultdict(list),
        "C2": defaultdict(list),
        "C3": defaultdict(list),
    }

    combined_hits = defaultdict(list)  # symbol -> ["1️⃣", "2️⃣"]

    # =========================
    # 스캔
    # =========================

    for symbol in symbols:
        sector = get_sector(symbol)

        try:
            c1 = condition_1_bb_rebound(symbol)
            c2 = condition_2_bb_rebound_with_volume(symbol)
            c3 = condition_3_bb_fibonacci(symbol)
        except Exception as e:
            print(f"[SCAN ERROR] {symbol}: {e}")
            continue

        if c1:
            hits["C1"][sector].append(symbol)
            combined_hits[symbol].append("1️⃣")

        if c2:
            hits["C2"][sector].append(symbol)
            combined_hits[symbol].append("2️⃣")

        if c3:
            hits["C3"][sector].append(symbol)
            combined_hits[symbol].append("3️⃣")

    # =========================
    # 텔레그램 메시지 구성
    # =========================

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    messages = [
        f"📡 Stock Scanner Status\n🕒 {now} ({TIMEZONE})"
    ]

    total_hits = sum(len(v) for cond in hits.values() for v in cond.values())

    # 조건별 상세
    for cond_key, cond_name in [
        ("C1", "1️⃣ BB 하단 터치 후 반등"),
        ("C2", "2️⃣ 반등 + 거래량 증가"),
        ("C3", "3️⃣ BB + 피보나치"),
    ]:
        section = [f"\n📌 {cond_name}"]
        has_any = False

        for sector, syms in hits[cond_key].items():
            if not syms:
                continue
            has_any = True
            section.append(f"- {sector}: {', '.join(syms[:MAX_PER_SECTOR])}")

        if has_any:
            messages.append("\n".join(section))

    # 복수 조건
    multi_condition = {
        s: c for s, c in combined_hits.items() if len(c) >= 2
    }

    if multi_condition:
        lines = ["\n🔥 복수 조건 동시 충족"]
        for symbol, conds in multi_condition.items():
            lines.append(f"- {symbol} ({' + '.join(conds)})")
        messages.append("\n".join(lines))

    # ❌ 조건 미충족 (무조건 1회)
    if total_hits == 0:
        messages.append("\n📭 조건을 만족하는 종목이 없습니다.\n(시스템 정상 동작)")

    # ⭐ Favorites 요약
    fav_hits = [s for s in FAVORITES if s in combined_hits]
    if fav_hits:
        messages.append("\n⭐ Favorites Hit\n" + ", ".join(fav_hits))
    else:
        messages.append("\n⭐ Favorites\n- 조건 충족 종목 없음")

    # =========================
    # 전송 (무조건 1회)
    # =========================

    send_message("\n".join(messages))
