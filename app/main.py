import yfinance as yf
from app.scanner import scan_symbol
from app.telegram import send_message
from app.universe import load_universe


def format_message(symbol, sector, triggered):
    label_map = {
        1: "① 볼린저 하단 반등",
        2: "② 반등 + 거래량 돌파",
        3: "③ 반등 + 피보나치 구간",
    }

    labels = " + ".join(label_map[i] for i in sorted(triggered))

    return (
        f"📊 <b>{symbol}</b>\n"
        f"🏷 섹터: {sector}\n"
        f"🚨 조건 발생: {labels}"
    )


def run():
    universe = load_universe(include_favorites=True, sanitize=True)

    messages = []

    for symbol, info in universe.items():
        try:
            df = yf.download(
                symbol,
                period="6mo",
                interval="1d",
                progress=False,
                auto_adjust=True,
                threads=False,
            )

            if df.empty:
                continue

            triggered = scan_symbol(df)

            if triggered:
                messages.append(
                    format_message(symbol, info["sector"], triggered)
                )

        except Exception as e:
            print(f"❌ {symbol} error: {e}")

    if messages:
        send_message("\n\n".join(messages))
    else:
        print("No signals today")
