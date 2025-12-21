from app.company_names import get_company_name
from app.price_utils import get_change_pct

def format_sector_message(sector, symbols, top_n=10):
    # symbols는 main에서 이미 "시총순 Top10"으로 들어옴 (선정 기준)
    symbols = symbols[:top_n]

    rows = []
    for s in symbols:
        pct = get_change_pct(s)
        rows.append((s, pct))

    up = [(s, pct) for s, pct in rows if pct is not None and pct > 0]
    down = [(s, pct) for s, pct in rows if pct is not None and pct < 0]
    flat = [(s, pct) for s, pct in rows if pct is not None and pct == 0]
    nodata = [(s, pct) for s, pct in rows if pct is None]

    # ✅ 표시 기준: 등락률 정렬
    up.sort(key=lambda x: x[1], reverse=True)    # + 큰 순
    down.sort(key=lambda x: x[1])               # - 작은 순(더 하락한 순)
    # flat은 그대로
    # nodata는 그대로

    lines = [
        f"📌 {sector} (Top {top_n} by MCap)",
        "-" * 28
    ]

    def _add_block(title, items, arrow):
        if not items:
            return
        lines.append(title)
        for s, pct in items:
            name = get_company_name(s)
            lines.append(f"• {s} ({name}) {arrow} {pct:+.2f}%")
        lines.append("")  # 블록 간 한 줄 띄움

    _add_block("🔺 상승", up, "🔺")
    _add_block("🔽 하락", down, "🔽")

    if flat:
        lines.append("⏸ 보합")
        for s, pct in flat:
            name = get_company_name(s)
            lines.append(f"• {s} ({name}) ⏸ {pct:+.2f}%")
        lines.append("")

    if nodata:
        lines.append("❓ 등락률 데이터 없음")
        for s, _ in nodata:
            name = get_company_name(s)
            lines.append(f"• {s} ({name})")
        lines.append("")

    # 마지막 빈 줄 정리
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def format_favorites(symbols):
    if not symbols:
        return None

    rows = [(s, get_change_pct(s)) for s in symbols]
    # 즐겨찾기는 보기 좋게 등락률 내림차순(데이터 없는 건 뒤)
    rows.sort(key=lambda x: (x[1] is None, -(x[1] or -999)))

    items = []
    for s, pct in rows:
        name = get_company_name(s)
        if pct is None:
            items.append(f"{s} ({name})")
        else:
            arrow = "🔺" if pct >= 0 else "🔽"
            items.append(f"{s} ({name}) {arrow} {pct:+.2f}%")

    return "⭐ 즐겨찾기 BB 하단 터치\n" + " / ".join(items)
