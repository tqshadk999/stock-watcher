from app.scanner import CONDITIONS
from app.favorites import FAVORITES
from app.telegram import send_message


def run():
    results = []

    # 🔍 전체 스캔
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

    # 📩 메시지 구성 (항상 전송)
    header = (
        "✅ 주식 스캔 완료\n"
        "⏱ 프리 · 정규 · 애프터 포함\n"
        f"📦 스캔 종목 수: {len(FAVORITES)}\n"
        "──────────────────\n"
    )

    if not results:
        message = header + "📭 조건 만족 종목 없음"
    else:
        message = header + "📊 조건 만족 종목\n\n" + "\n".join(results)

    send_message(message)
