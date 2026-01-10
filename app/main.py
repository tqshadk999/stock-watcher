from app.scanner import scan_symbol
from app.favorites import FAVORITES
from app.telegram import send_message


def run():
    messages = []

    for symbol in FAVORITES:
        try:
            result = scan_symbol(symbol)

            hits = []
            if result["bb_rebound"]:
                hits.append("BB Rebound")
            if result["bb_rebound_volume"]:
                hits.append("BB Rebound + Volume")
            if result["bb_rebound_fib"]:
                hits.append("BB Rebound + Fib")

            if hits:
                msg = f"📈 {symbol}\n" + "\n".join(f"- {h}" for h in hits)
                messages.append(msg)

        except Exception as e:
            # 개별 종목 실패는 전체 중단 방지
            continue

    if messages:
        send_message("\n\n".join(messages))
