import os
from collections import defaultdict

from app.universe import load_universe, attach_market_cap
from app.scanner import intraday_bb_rebound, intraday_bb_touch
from app.state import should_alert, mark_alerted
from app.formatter import format_sector_message, format_favorites
from app.telegram import send_message


TOP_PER_SECTOR = 10


def run():
    # 수동 실행(workflow_dispatch)이면 강제 알림
    force_notify = os.getenv("FORCE_NOTIFY", "0") == "1"

    # 1️⃣ 유니버스 로드 (S&P500 + Nasdaq100 + Favorites, sanitize 포함)
    symbols = load_universe(include_favorites=True, sanitize=True)

    # 2️⃣ 시총/섹터 정보 부착
    df = attach_market_cap(symbols)
    if df is None or df.empty:
        if force_notify:
            send_message("⚠️ 실행 실패: 유니버스 데이터가 비어있습니다.")
        return

    # 3️⃣ 즐겨찾기 sanitize (유효한 것만)
    from app.favorites import FAVORITES
    from app.ticker_sanitize import sanitize_symbols

    favorites_valid, favorites_dropped = sanitize_symbols(
        [s.replace(".", "-") for s in FAVORITES]
    )
    favorites_set = set(favorites_valid)

    # 4️⃣ 결과 컨테이너
    # sector -> [(symbol, market_cap)]
    sector_hits = defaultdict(list)
    favorite_hits = []

    # 5️⃣ 스캔 루프
    for row in df.itertuples():
        symbol = row.symbol

        # 스케줄 실행이면 중복 방지 적용
        if not force_notify and not should_alert(symbol):
            continue

        # ⭐ 즐겨찾기: BB 하단 터치만
        if symbol in favorites_set:
            if intraday_bb_touch(symbol):
                favorite_hits.append(symbol)
                if not force_notify:
                    mark_alerted(symbol)
            continue

        # 📌 일반 종목: BB 하단 터치 + 반등 + 거래량 조건(scanner 내부)
        if intraday_bb_rebound(symbol):
            sector_hits[row.sector].append((symbol, row.market_cap))
            if not force_notify:
                mark_alerted(symbol)

    # 6️⃣ 섹터별 시총 Top10 → 출력
    sent_any = False

    for sector, items in sector_hits.items():
        # 시총 내림차순
        items.sort(key=lambda x: x[1] or 0, reverse=True)
        top_symbols = [s for s, _ in items[:TOP_PER_SECTOR]]

        if top_symbols:
            send_message(
                format_sector_message(
                    sector,
                    top_symbols,
                    top_n=TOP_PER_SECTOR
                )
            )
            sent_any = True

    # 7️⃣ 즐겨찾기 요약 (1줄)
    fav_msg = format_favorites(favorite_hits)
    if fav_msg:
        send_message(fav_msg)
        sent_any = True

    # 8️⃣ 수동 실행인데 신호가 하나도 없으면 확인 메시지
    if force_notify and not sent_any:
        send_message("✅ 수동 실행 완료: 조건을 만족한 종목이 없습니다.")

    # (선택) 즐겨찾기 중 자동 제외된 티커 알림
    # if force_notify and favorites_dropped:
    #     send_message(
    #         "⚠️ 즐겨찾기 중 yfinance 조회 실패로 제외됨:\n"
    #         + ", ".join(favorites_dropped)
    #     )
