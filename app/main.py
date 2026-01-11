from app.scanner import CONDITIONS
from app.favorites import FAVORITES
from app.telegram import send_message


def run():
    results = []

    for symbol in FAVORITES:
        matched = []

        for code, func in CONDITIONS.items():
            try:
                if func(symbol):
                    matched.append(code)
            except Exception:
                continue

        if matched:
            results.append(f"{symbol} → [{' + '.join(matched)}]")

    if not results:
        send_message("📭 스캔 완료\n조건 만족 종목 없음")
        return

    message = (
        "📊 조건 만족 종목 발견\n"
        "(프리 · 정규 · 애프터 포함)\n\n"
        + "\n".join(results)
    )

    send_message(message)
