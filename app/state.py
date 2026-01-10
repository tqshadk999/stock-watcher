_alerted = set()

def should_alert(symbol):
    return symbol not in _alerted

def mark_alerted(symbol):
    _alerted.add(symbol)
