# app/main.py
import os
import time
from datetime import datetime, date
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from app.notifier import send_message  # send_photo는 안 씀 (최적화)
from app.scanner import (
    load_universe,
    load_price_daily,
    add_indicators,
    evaluate_conditions,
    get_market_cap,
    get_company_name,
    load_sent_state,
    save_sent_state,
)

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))  # 로컬용, Actions는 env로 들어옴

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# 하루 3번 추천에서 "종목 겹침 방지" 저장 파일
SENT_STATE_PATH = os.getenv("SENT_STATE_PATH", os.path.join(BASE_DIR, "sent_state.json"))

# 스캔 범위 (너무 오래 잡으면 느려짐)
PRICE_PERIOD = os.getenv("PRICE_PERIOD", "180d")

# 섹터별 최대 추천 개수
TOP_PER_SECTOR = int(os.getenv("TOP_PER_SECTOR", "10"))

# 최소 후보 데이터 길이
MIN_BARS = int(os.getenv("MIN_BARS", "60"))


def _fmt_cap(v: int) -> str:
    # 메시지 가독성용 (선택)
    if v >= 1_000_000_000_000:
        return f"{v/1_000_000_000_000:.2f}T"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    return str(v)


def build_sector_top10_message(candidates_by_sector: Dict[str, List[Tuple[str, str, int]]]) -> str:
    """
    candidates_by_sector[sector] = [(symbol, name, marketcap), ...]  (이미 정렬된 상태)
    """
    lines: List[str] = []
    lines.append("📌 *[Stock Watcher] 조건 충족 종목 (섹터별 시총 Top)*")
    lines.append("조건: *볼린저 밴드 하단 터치 후 반등*")
    lines.append("범위: S&P500 + NASDAQ100 (일봉)")
    lines.append("")

    # 섹터명 정렬
    for sector in sorted(candidates_by_sector.keys()):
        items = candidates_by_sector[sector]
        if not items:
            continue
        lines.append(f"✅ *{sector}*")
        for sym, nm, cap in items:
            lines.append(f"• [{sym}] {nm}  (MC: {_fmt_cap(cap)})")
        lines.append("")

    if len(lines) <= 5:
        return "📌 *[Stock Watcher]* 오늘 조건에 맞는 종목이 없습니다."
    return "\n".join(lines)


def run_cloud_once() -> None:
    """
    GitHub Actions / 수동 실행용: 한 번만 스캔하고, 섹터별 Top10 추천 메시지 발송
    - 하루(08/12/22) 동안 이미 보낸 종목은 제외 (sent_state.json)
    """
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN / CHAT_ID 환경변수가 비어 있습니다. (Actions secrets 확인)")

    universe = load_universe()
    if not universe:
        send_message(TELEGRAM_TOKEN, CHAT_ID, "❌ Universe 로딩 실패 (위키 파싱 오류 가능)")
        return

    today_str = date.today().isoformat()
    saved_date, sent_list = load_sent_state(SENT_STATE_PATH)
    sent_set = set(sent_list)

    # 날짜 바뀌면 초기화
    if saved_date != today_str:
        sent_set = set()

    # 후보 수집: 조건 충족 종목만
    raw_candidates: List[Tuple[str, str, str]] = []  # (sector, symbol, name)
    for it in universe:
        df = load_price_daily(it.symbol, period=PRICE_PERIOD)
        if df is None or len(df) < MIN_BARS:
            continue
        df = add_indicators(df)
        conds = evaluate_conditions(df)
        if not conds["trigger"]:
            continue
        raw_candidates.append((it.sector or "UNKNOWN", it.symbol, it.name or it.symbol))

        # 너무 느려지면 안전장치 (원하면 제거)
        time.sleep(0.05)

    # 시총 조회 + 섹터별로 모으기
    by_sector: Dict[str, List[Tuple[str, str, int]]] = {}
    for sector, sym, nm in raw_candidates:
        if sym in sent_set:
            continue  # ✅ 하루 중복 방지

        cap = get_market_cap(sym)
        if cap <= 0:
            continue

        name = get_company_name(sym, fallback=nm)
        by_sector.setdefault(sector, []).append((sym, name, cap))

        # yfinance 과다 호출 방지
        time.sleep(0.1)

    # 섹터별 시총 내림차순, Top10만
    final: Dict[str, List[Tuple[str, str, int]]] = {}
    newly_sent: List[str] = []
    for sector, items in by_sector.items():
        items_sorted = sorted(items, key=lambda x: x[2], reverse=True)
        picked = items_sorted[:TOP_PER_SECTOR]
        if picked:
            final[sector] = picked
            newly_sent += [s for s, _, _ in picked]

    msg = build_sector_top10_message(final)
    send_message(TELEGRAM_TOKEN, CHAT_ID, msg, parse_mode="Markdown")

    # 상태 저장 (이번 런에서 보낸 종목을 누적)
    sent_set.update(newly_sent)
    save_sent_state(SENT_STATE_PATH, today_str, sorted(list(sent_set)))


# 로컬 테스트용
if __name__ == "__main__":
    run_cloud_once()
