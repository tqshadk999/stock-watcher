from app.company_names import get_company_name
from app.price_utils import get_change_pct

TOP_N = 5  # 🔥 섹터별 최대 출력 개수

def _sorted_by_pct(symbols):
    rows = []
    for s in symbols:
        rows.append((s, get_change_pct(s)))
    # 등락률 내림차순, None은 맨 아래
    rows.sort(key=lambda x: (x[1] is None, -(x[1] or -999)))
    return rows

def format_sector_message(sector, symbols):
    rows = _sorted_by_pct(symbols)[:TOP_N]  # 🔥 Top N 컷

    lines = [
        f"📌 {sector} (Top {TOP_N})",
        "-" * 22
    ]

    for s, pct in rows:
        name = get_company_name(s)
        if pct is None:
            lines.append(f"• {s} ({name})")
        else:
            arrow = "🔺" if pct >= 0 else "🔽"
            lines.append(f"• {s} ({name}) {arrow} {pct:+.2f}%")

    return "\n".join(lines)


def format_favorites(symbols):
    rows = _sorted_by_pct(symbols)  # 즐겨찾기는 컷 없이 전부 표시

    items = []
    for s, pct in rows:
        name = get_company_name(s)
        if pct is None:
            items.append(f"{s} ({name})")
        else:
            arrow = "🔺" if pct >= 0 else "🔽"
            items.append(f"{s} ({name}) {arrow} {pct:+.2f}%")

    return "⭐ 즐겨찾기 BB 하단 터치\n" + " / ".join(items) if items else None
