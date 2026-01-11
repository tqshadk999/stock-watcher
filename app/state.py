import os
import json
from datetime import date

STATE_FILE = "alert_state.json"


def _load():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def _save(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def should_alert(symbol: str) -> bool:
    data = _load()
    today = str(date.today())
    return data.get(symbol) != today


def mark_alerted(symbol: str):
    data = _load()
    data[symbol] = str(date.today())
    _save(data)
