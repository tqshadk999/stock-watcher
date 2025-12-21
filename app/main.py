from collections import defaultdict

from app.universe import load_universe, attach_market_cap
from app.scanner import intraday_bb_rebound, intraday_bb_touch
from app.state import should_alert, mark_alerted
from app.formatter import format_sector_message, format_favorites
from app.telegram import send_message

TOP_PER_SECTOR = 10

def run():
    # ✅ 유니버스는 sanitize 포함
    symbols = load_universe(include_favorites=True, sanitize=True)
    df = attach_market_cap(symbols)

    # ✅ 즐겨찾기만 따로 sanitize해서 사용 (오류 최소화)
    from app.favorites import FAVORITES
    from app.ticker_sanitize import sanitize_symbols
    favorites_valid, favorites_dropped = sanitize_symbols([s.replace(".", "-") for s in FAVORITES])
    favorites_set = set(favorites_valid)

    sector_hits = defaultdict(list)
    favorite_hits = []

    for row in df.itertuples():
        symbol = row.symbol

        if not should_alert(symbol):
            continue

        # ⭐ 즐겨찾기: BB 하단 터치만
        if symbol in favorites_set:
            if intraday_bb_touch(symbol):
                favorite_hits.append(symbol)
                mark_alerted(symbol)
            continue

        # 📌 일반: 하단 터치 + 반등 + 거래량(스캐너 내부)
        if intraday_bb_rebound(symbol):
            sector_hits[row.sector].append((symbol, row.market_cap))
            mark_alerted(symbol)

    # 섹터별 시총 Top10 컷
    for sector, items in sector_hits.items():
        items.sort(key=lambda x: x[1] or 0, reverse=True)
        top_symbols = [s for s, _ in items[:TOP_PER_SECTOR]]
        send_message(format_sector_message(sector, top_symbols, top_n=TOP_PER_SECTOR))

    # 즐겨찾기 1줄
    fav_msg = format_favorites(favorite_hits)
    if fav_msg:
        send_message(fav_msg)

    # (선택) 실패 티커를 조용히 로그만 남기고 싶으면:
    # if favorites_dropped:
    #     send_message("⚠️ 즐겨찾기 중 조회 실패(자동 제외): " + ", ".join(favorites_dropped))
