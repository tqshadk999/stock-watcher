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

TOP10 = 10


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


def _today() -> str:
    return date.today().isoformat()


def _mcap(sym: str) -> int:
    try:
        info = yf.Ticker(sym).info
        return int(info.get("marketCap") or 0)
    except Exception:
        return 0


def report_theme_top10() -> None:
    today = _today()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    found = _load_json(FOUND_FILE, {"date": today, "items": []})
    if found.get("date") != today:
        found = {"date": today, "items": []}

    sent = _load_json(SENT_FILE, {"date": today, "sent_symbols": []})
    if sent.get("date") != today:
        sent = {"date": today, "sent_symbols": []}

    sent_set = set(sent.get("sent_symbols", []))

    candidates = [it for it in found.get("items", []) if it.get("symbol") and it["symbol"] not in sent_set]

    # ✅ 요약 메시지는 무조건 1번
    if not candidates:
        send_message(
            f"📊 *조건 스캔 요약*\n기준: {now}\n\n"
            "⚠️ 조건 충족 종목이 없거나, 오늘 이미 전부 발송되었습니다.",
            parse_mode="Markdown",
        )
        return

    # 테마별 분리
    by_theme = {}
    for it in candidates:
        by_theme.setdefault(it.get("theme", "기타"), []).append(it)

    lines = [
        "📊 *미국주식 테마별 조건 충족 Top10*",
        "조건: 볼린저 하단 반등 / (2일 하락 후 반등 포함)",
        f"기준시각: {now}",
        "",
    ]

    newly_sent = set()

    # 테마별 시총 Top10
    for theme in ["반도체", "금/은/원자재", "AI", "배당주"]:
        items = by_theme.get(theme, [])
        if not items:
            continue

        ranked = []
        for it in items:
            sym = it["symbol"]
            ranked.append((_mcap(sym), it))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top = ranked[:TOP10]

        if not top:
            continue

        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append(f"{theme} :")
        for mcap, it in top:
            sym = it["symbol"]
            name = it.get("name", "")
            lines.append(f"[{sym}] {name}")
            newly_sent.add(sym)

    send_message("\n".join(lines), parse_mode="Markdown")

    # 하루 중복 방지 저장
    sent_set |= newly_sent
    sent["date"] = today
    sent["sent_symbols"] = sorted(sent_set)
    _save_json(SENT_FILE, sent)


def run(mode: str) -> None:
    if mode == "scan":
        scan_and_store()
    elif mode == "report":
        report_theme_top10()
    else:
        raise ValueError("MODE는 scan 또는 report")


if __name__ == "__main__":
    run(os.getenv("MODE", "report").strip().lower())
