from app.company_names import get_company_name
from app.price_utils import get_change_pct

TOP_N = 5

def format_sector_message(sector, symbols):
    rows = [(s, get_change_pct(s)) for s in symbols]
    rows.sort(key=lambda x: (x[1] is None, -(x[1] or -999)))
    rows = rows[:TOP_N]

    lines = [f"📌 {sector} (Top {TOP_N})", "-"*22]
    for s, pct in rows:
        name = get_company_name(s)
        arrow = "🔺" if pct and pct >= 0 else "🔽"
        lines.append(f"• {s} ({name}) {arrow} {pct:+.2f}%")
    return "\n".join(lines)

def format_favorites(symbols):
    rows = [(s, get_change_pct(s)) for s in symbols]
    rows.sort(key=lambda x: (x[1] is None, -(x[1] or -999)))

    items = []
    for s, pct in rows:
        name = get_company_name(s)
        arrow = "🔺" if pct and pct >= 0 else "🔽"
        items.append(f"{s} ({name}) {arrow} {pct:+.2f}%")

    return "⭐ 즐겨찾기 BB 하단 터치\n" + " / ".join(items) if items else None
