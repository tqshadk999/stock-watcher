# app/main.py
from __future__ import annotations

import os, json
from datetime import date, datetime

import yfinance as yf

from app.notifier import send_message
from app.scanner import scan_and_store

DATA_DIR = "data"
FOUND_FILE = os.path.join(DATA_DIR, "found_today.json")
SENT_FILE = os.path.join(DATA_DIR, "sent_today.json")

TOP_N_PER_THEME = 10


def _load_json(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _today_key() -> str:
    return date.today().isoformat()


def _get_market_cap(symbol: str) -> int:
    try:
        info = yf.Ticker(symbol).info
        return int(info.get("marketCap", 0) or 0)
    except Exception:
        return 0


def send_theme_top10_report() -> None:
    """
    알림 시간(08/12/22 등) 실행:
    - found_today.json에서 조건 충족 종목 로드
    - sent_today.json에 기록된 종목은 제외 (하루 기준 중복 방지)
    - 테마별로 시총순 Top10만 텔레그램 전송
    - 전송된 종목은 sent_today.json에 저장
    """
    today = _today_key()

    found = _load_json(FOUND_FILE, {"date": today, "items": []})
    if found.get("date") != today:
        found = {"date": today, "items": []}

    sent = _load_json(SENT_FILE, {"date": today, "sent_symbols": []})
    if sent.get("date") != today:
        sent = {"date": today, "sent_symbols": []}

    sent_set = set(sent.get("sent_symbols", []))

    # 아직 안 보낸 후보만
    candidates = []
    for it in found.get("items", []):
        sym = it.get("symbol")
        if not sym or sym in sent_set:
            continue
        candidates.append(it)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ✅ 실행 확인/요약은 무조건 1번 보냄
    if not candidates:
        send_message(
            f"📊 *조건 스캔 요약*\n"
            f"기준: {now}\n\n"
            f"⚠️ 오늘(또는 현재까지) 조건 충족 종목이 없거나,\n"
            f"이미 오늘 알림으로 모두 발송되었습니다.",
            parse_mode="Markdown",
        )
        return

    # 테마별 그룹
    by_theme: dict[str, list[dict]] = {}
    for it in candidates:
        theme = it.get("theme", "기타") or "기타"
        by_theme.setdefault(theme, []).append(it)

    # 테마별 Top10(시총)
    final_lines = [
        "📊 *미국주식 테마별 조건 충족 Top 10*",
        "조건: 볼린저 하단 반등 / (2일 하락 후 반등 포함)",
        f"기준시각: {now}",
        "",
    ]

    newly_sent = set()

    for theme in sorted(by_theme.keys()):
        items = by_theme[theme]

        ranked = []
        for it in items:
            sym = it["symbol"]
            mcap = _get_market_cap(sym)
            ranked.append((mcap, it))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top = ranked[:TOP_N_PER_THEME]

        if not top:
            continue

        final_lines.append("━━━━━━━━━━━━━━━━━━")
        final_lines.append(f"{theme} :")
        for mcap, it in top:
            sym = it["symbol"]
            name = it.get("name", "")
            final_lines.append(f"[{sym}] {name}")
            newly_sent.add(sym)

    # 전송
    send_message("\n".join(final_lines), parse_mode="Markdown")

    # sent 저장(하루 중복 방지)
    sent_set |= newly_sent
    sent["date"] = today
    sent["sent_symbols"] = sorted(sent_set)
    _save_json(SENT_FILE, sent)


# =========================
# 실행 진입점
# =========================
def run(mode: str) -> None:
    """
    mode:
      - scan   : 장중 감시(누적 저장)
      - report : 알림시간 리포트(테마별 Top10, 중복 제거)
    """
    if mode == "scan":
        scan_and_store()
    elif mode == "report":
        send_theme_top10_report()
    else:
        raise ValueError("mode는 scan 또는 report 이어야 합니다.")


if __name__ == "__main__":
    # 기본은 report (원하면 환경변수 MODE로 변경)
    mode = os.getenv("MODE", "report").strip().lower()
    run(mode)
