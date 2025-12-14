# app/scanner.py
from __future__ import annotations

import os, json
from datetime import date, datetime

import yfinance as yf
import pandas as pd

from app.universe import build_theme_top100

DATA_DIR = "data"
FOUND_FILE = os.path.join(DATA_DIR, "found_today.json")

LOOKBACK_DAYS = 90


def _load_found() -> dict:
    today = date.today().isoformat()
    if not os.path.exists(FOUND_FILE):
        return {"date": today, "items": []}
    try:
        with open(FOUND_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != today:
            return {"date": today, "items": []}
        if "items" not in data:
            data["items"] = []
        return data
    except Exception:
        return {"date": today, "items": []}


def _save_found(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FOUND_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_condition(df: pd.DataFrame) -> bool:
    """
    조건:
    - 볼린저 하단 터치 후 반등
    - 또는 2일 연속 하락 후 반등(완화)
    """
    if len(df) < 25:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    lower = ma20 - 2 * std20

    c2, c1, c0 = close.iloc[-3], close.iloc[-2], close.iloc[-1]

    cond_boll = (c1 <= lower.iloc[-2]) and (c0 > c1)
    cond_2down_rebound = (c2 > c1 and c1 > c0) or (c2 > c1 and c0 > c1)

    return cond_boll or cond_2down_rebound


def scan_and_store() -> None:
    """
    테마별 시총 Top100 universe만 스캔(속도/안정)
    조건 충족 종목을 하루 기준 누적 저장
    """
    found = _load_found()
    existing = {x.get("symbol") for x in found["items"] if x.get("symbol")}

    theme_top100 = build_theme_top100()

    for theme, arr in theme_top100.items():
        for sym, name, _mcap in arr:
            if sym in existing:
                continue

            try:
                df = yf.download(sym, period=f"{LOOKBACK_DAYS}d", interval="1d", progress=False)
                if df is None or df.empty:
                    continue

                if check_condition(df):
                    found["items"].append({
                        "symbol": sym,
                        "name": name,
                        "theme": theme,
                        "hit_time": datetime.now().strftime("%H:%M"),
                    })
                    existing.add(sym)

            except Exception:
                continue

    _save_found(found)
