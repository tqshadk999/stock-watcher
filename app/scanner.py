# app/scanner.py
from __future__ import annotations

import os
import json
from datetime import date, datetime

import yfinance as yf
import pandas as pd

from app.universe import (
    get_sp500,
    get_nasdaq100,
    get_dowjones,
    classify_theme,
)

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "found_today.json")

LOOKBACK_DAYS = 90


# =========================
# 저장소 준비
# =========================
def load_state() -> dict:
    today = date.today().isoformat()
    if not os.path.exists(STATE_FILE):
        return {"date": today, "symbols": []}

    with open(STATE_FILE, "r") as f:
        data = json.load(f)

    if data.get("date") != today:
        return {"date": today, "symbols": []}

    return data


def save_state(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# =========================
# 조건: 볼린저 하단 반등
# =========================
def check_condition(df: pd.DataFrame) -> bool:
    if len(df) < 25:
        return False

    close = df["Close"]
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    lower = ma20 - 2 * std20

    return close.iloc[-2] <= lower.iloc[-2] and close.iloc[-1] > close.iloc[-2]


# =========================
# 장중 감시 (누적 저장)
# =========================
def scan_and_store():
    state = load_state()
    stored = set(state["symbols"])

    universe = pd.concat([
        get_sp500(),
        get_nasdaq100(),
        get_dowjones(),
    ]).drop_duplicates("Symbol")

    for _, row in universe.iterrows():
        symbol = row["Symbol"]
        name = row["Security"]

        if symbol in stored:
            continue

        try:
            df = yf.download(
                symbol,
                period=f"{LOOKBACK_DAYS}d",
                interval="1d",
                progress=False,
            )
            if df.empty:
                continue

            if check_condition(df):
                theme = classify_theme(name)
                stored.add(symbol)

                state["symbols"].append({
                    "symbol": symbol,
                    "name": name,
                    "theme": theme,
                    "time": datetime.now().strftime("%H:%M"),
                })

        except Exception:
            continue

    save_state(state)
