# app/main.py
import json
import os
from datetime import datetime

import yfinance as yf

from app.notifier import send_message

STATE_FILE = "data/found_today.json"
TOP_N = 10


def send_top10():
    if not os.path.exists(STATE_FILE):
        send_message("⚠️ 오늘 조건 충족 종목이 없습니다.")
        return

    with open(STATE_FILE, "r") as f:
        data = json.load(f)

    results = []
    for item in data["symbols"]:
        try:
            info = yf.Ticker(item["symbol"]).info
            mcap = info.get("marketCap", 0)
            results.append((item, mcap))
        except Exception:
            continue

    if not results:
        send_message("⚠️ 오늘 조건 충족 종목이 없습니다.")
        return

    results.sort(key=lambda x: x[1], reverse=True)
    top = results[:TOP_N]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    msg = [
        "📊 *조건 충족 종목 시총 Top 10*",
        "조건: 볼린저 밴드 하단 반등",
        f"기준시각: {now}",
        "",
    ]

    for i, (item, _) in enumerate(top, 1):
        msg.append(
            f"{i}. [{item['symbol']}] {item['name']} ({item['theme']})"
        )

    send_message("\n".join(msg), parse_mode="Markdown")


def run_cloud_once():
    send_top10()


if __name__ == "__main__":
    run_cloud_once()
