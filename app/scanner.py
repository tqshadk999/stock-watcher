# app/scanner.py
from __future__ import annotations

import os, json
from datetime import date, datetime

import yfinance as yf
import pandas as pd

from app.universe import get_sp500, get_nasdaq100, get_dowjones, classify_theme

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
    - 또는 2일 연속 하락 후 반등 (완화)
    """
    if len(df) < 25:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    lower = ma20 - 2 * std20

    c2, c1, c0 = close.iloc[-3], close.iloc[-2], close.iloc[-1]

    cond_boll = (c1 <= lower.iloc[-2]) and (c0 > c1)
    cond_2down_rebound = (c2 > c1 > c0) or (c2 > c1 and c0 > c1)

    return cond_boll or cond_2down_rebound


def scan_and_store() -> None:
    """
    장중(또는 원하는 주기) 실행:
    - S&P500 + NASDAQ100 + DowJones 유니버스 스캔
    - 조건 충족 종목을 data/found_today.json 에 누적 저장
    - 하루 기준 중복 저장 방지
    """
    found = _load_found()
    existing = {x["symbol"] for x in found["items"] if "symbol" in x}

    universe = pd.concat([get_sp500(), get_nasdaq100(), get_dowjones()]).drop_duplicates("Symbol")

    for _, row in universe.iterrows():
        symbol = str(row["Symbol"]).strip()
        name = str(row["Security"]).strip()

        if not symbol or symbol in existing:
            continue

        try:
            df = yf.download(symbol, period=f"{LOOKBACK_DAYS}d", interval="1d", progress=False)
            if df is None or df.empty:
                continue

            if check_condition(df):
                theme = classify_theme(name)
                found["items"].append({
                    "symbol": symbol,
                    "name": name,
                    "theme": theme,
                    "hit_time": datetime.now().strftime("%H:%M"),
                })
                existing.add(symbol)
        except Exception:
            continue

    _save_found(found)
