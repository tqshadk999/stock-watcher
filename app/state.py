import json, os
from datetime import date

FILE = "alert_state.json"

def _load():
    if not os.path.exists(FILE):
        return {"date": str(date.today()), "sent": []}
    return json.load(open(FILE))

def should_alert(symbol):
    s = _load()
    return s["date"] != str(date.today()) or symbol not in s["sent"]

def mark_alerted(symbol):
    s = _load()
    if s["date"] != str(date.today()):
        s = {"date": str(date.today()), "sent": []}
    s["sent"].append(symbol)
    json.dump(s, open(FILE,"w"))
