def format_message(symbol, sector, conditions):
    cond_map = {
        "C1": "1️⃣ 볼린저 하단 반등",
        "C2": "2️⃣ 볼린저 하단 반등 + 거래량 증가",
        "C3": "3️⃣ 볼린저 + 피보나치"
    }

    lines = "\n".join(cond_map[c] for c in conditions)

    return f"""
📊 종목 시그널 감지

▪️ 종목: {symbol}
▪️ 산업군: {sector}

🚨 발생 조건:
{lines}
""".strip()
