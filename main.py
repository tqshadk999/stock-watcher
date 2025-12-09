# main.py  – 공통 로직 (로컬/클라우드에서 같이 사용)

import os
import time
import logging
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv

from notifier import send_message, send_photo
from utils import (
    get_sp500_tickers,
    get_nasdaq100_tickers,
    safe_download_symbol,
    add_indicators,
    evaluate_conditions,
    top_n_by_marketcap,
    get_company_name,          # 종목 코드 → 회사 이름
)

# ─────────────────────────────
# 환경 변수 로드
# ─────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# 로컬에서는 CHAT_ID, GitHub Secrets에서는 TELEGRAM_CHAT_ID 를 써도 되도록 둘 다 지원
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "30"))
TOPN = int(os.getenv("TOPN", "10"))

TOPN_TIMES = ["08:00", "13:00", "22:00"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [main] %(message)s")
logger = logging.getLogger(__name__)

# 전역 티커 리스트
sp500_tickers: list[str] = []
nasdaq_tickers: list[str] = []
combined: list[tuple[str, str]] = []  # (index_name, symbol)

cursor: int = 0
last_alert_time: dict[tuple[str, str], datetime] = {}
last_topn_sent: dict[tuple[str, str], date] = {}


# ─────────────────────────────
# 차트 생성 (Price + MFI, 최근 60일 일봉)
# ─────────────────────────────
def build_price_mfi_chart(df: pd.DataFrame, symbol: str, index_name: str) -> bytes:
    """
    - 위: 캔들 + MA20/60/120 + 볼린저밴드(노란선)
    - 아래: MFI (80/20 기준선)
    - 모두 최근 60 영업일 기준
    """
    df = df.tail(60).copy()
    if df.empty:
        raise ValueError("No data to plot")

    # 보조지표 보장
    df = add_indicators(df)

    dates = mdates.date2num(df.index.to_pydatetime())

    fig = plt.figure(figsize=(11, 8))

    # 1) 가격 패널
    ax1 = fig.add_subplot(211)

    candle_width = 0.6

    for x, o, h, l, c in zip(dates, df["Open"], df["High"], df["Low"], df["Close"]):
        if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c):
            continue
        is_bull = c >= o
        color = "red" if is_bull else "blue"

        # 심지
        ax1.vlines(x, l, h, color=color, linewidth=1.0, zorder=3)
        # 몸통
        body_bottom = min(o, c)
        body_top = max(o, c)
        height = body_top - body_bottom or 0.001
        ax1.add_patch(
            plt.Rectangle(
                (x - candle_width / 2.0, body_bottom),
                candle_width,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.5,
                zorder=3,
            )
        )

    # 이평선
    ax1.plot(dates, df["MA20"], color="limegreen", label="MA20", linewidth=1, zorder=1)
    ax1.plot(dates, df["MA60"], color="orange", label="MA60", linewidth=1, zorder=1)
    ax1.plot(dates, df["MA120"], color="purple", label="MA120", linewidth=1, zorder=1)

    # 볼린저
    ax1.plot(dates, df["Upper"], color="gold", linestyle="--", linewidth=0.9, label="Upper", zorder=0)
    ax1.plot(dates, df["Lower"], color="gold", linestyle="--", linewidth=0.9, label="Lower", zorder=0)
    ax1.fill_between(
        dates,
        df["Lower"],
        df["Upper"],
        facecolor="#fff9c4",
        alpha=0.4,
        zorder=-1,
    )

    ax1.set_ylabel("Price")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

    # 2) MFI 패널
    ax2 = fig.add_subplot(212, sharex=ax1)
    ax2.plot(dates, df["MFI"], color="purple", linewidth=1.5)
    ax2.set_ylabel("MFI")
    ax2.set_ylim(0, 100)
    ax2.axhline(80, color="red", linestyle="--", linewidth=0.8)
    ax2.axhline(20, color="green", linestyle="--", linewidth=0.8)

    ax2.xaxis_date()
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")

    fig.suptitle(f"{index_name} / {symbol}", fontsize=14)

    fig.tight_layout(rect=[0, 0, 1, 0.96])

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────
# 티커 로딩
# ─────────────────────────────
def init_tickers():
    global sp500_tickers, nasdaq_tickers, combined
    sp500_tickers = get_sp500_tickers()
    nasdaq_tickers = get_nasdaq100_tickers()
    combined = [("S&P500", s) for s in sp500_tickers] + [("NASDAQ100", s) for s in nasdaq_tickers]
    logger.info(f"Loaded {len(sp500_tickers)} S&P500, {len(nasdaq_tickers)} NASDAQ100 tickers")


# ─────────────────────────────
# 단일 종목 조건 검사 + 알림
# ─────────────────────────────
def check_symbol_and_alert(index_name: str, symbol: str, now: datetime):
    try:
        # GitHub용: 일봉 기준
        df = safe_download_symbol(symbol, period="120d", interval="1d")
        if df is None or df.empty:
            return

        df = add_indicators(df)
        conds = evaluate_conditions(df)
        if not conds["trigger"]:
            return

        key = (index_name, symbol)
        last_time = last_alert_time.get(key)
        # 2시간 이내 중복 알림 방지 (로컬 24/7 돌릴 때용)
        if last_time and (now - last_time).total_seconds() < 7200:
            return

        company_name = get_company_name(symbol) or ""
        display_name = f"{symbol} {company_name}".strip()

        # 텍스트
        text_lines = [f"*{index_name} / {display_name}*"]
        if conds["bollinger_rebound"]:
            text_lines.append("• 볼린저 밴드 하단 터치 후 반등")
        if conds["breakout_90d"]:
            text_lines.append("• 최근 90일 신고가 돌파")
        if conds["mfi_strong"]:
            text_lines.append("• MFI 강세 (50 이상)")
        if conds["volume_strong"]:
            text_lines.append("• 거래량 20MA 상회")

        # 시가/종가/현재가 (일봉 기준 → 현재가 = 마지막 종가)
        last_row = df.iloc[-1]
        o = float(last_row["Open"])
        c = float(last_row["Close"])
        text_lines.append("")
        text_lines.append(f"시가: {o:,.2f}")
        text_lines.append(f"종가(=현재가): {c:,.2f}")

        text_lines.append(f"\n시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        caption = "\n".join(text_lines)

        chart_bytes = build_price_mfi_chart(df, symbol, index_name)
        send_photo(TELEGRAM_TOKEN, CHAT_ID, chart_bytes, caption=caption, parse_mode="Markdown")

        last_alert_time[key] = now
        time.sleep(1.0)
    except Exception as e:
        logger.warning(f"Error processing {index_name} {symbol}: {e}")


# ─────────────────────────────
# (선택) TopN 추천 - 로컬에서만 사용
# ─────────────────────────────
def maybe_send_topn(now: datetime):
    today = now.date()
    current_hm = now.strftime("%H:%M")

    if current_hm not in TOPN_TIMES:
        return

    for index_name in ["S&P500", "NASDAQ100"]:
        key = (index_name, current_hm)
        if last_topn_sent.get(key) == today:
            continue

        logger.info(f"Sending Top{TOPN} for {index_name} at {current_hm}")
        symbols = get_sp500_tickers() if index_name == "S&P500" else get_nasdaq100_tickers()

        matched = []
        for s in symbols:
            try:
                df = safe_download_symbol(s, period="200d", interval="1d")
                if df is None or df.empty:
                    continue
                df = add_indicators(df)
                conds = evaluate_conditions(df)
                if conds["trigger"]:
                    matched.append(s)
            except Exception:
                continue

        target_list = matched if matched else symbols
        top = top_n_by_marketcap(target_list, n=TOPN)

        text = f"📊 *{index_name} Top {TOPN} 후보*\n"
        text += "(조건: 볼린저 반등/신고가 + 시총 상위)\n\n"
        text += "\n".join([f"{i+1}. `{sym}`" for i, sym in enumerate(top)])

        send_message(TELEGRAM_TOKEN, CHAT_ID, text)
        last_topn_sent[key] = today
        time.sleep(1.0)


# ─────────────────────────────
# 로컬에서 24/7 돌릴 때 사용하는 main()
# (GitHub Actions에서는 사용 안 하고, cloud_scan_once.py가 run_once만 호출)
# ─────────────────────────────
def main():
    global cursor

    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError(".env 또는 GitHub Secrets의 TELEGRAM_TOKEN / CHAT_ID가 비어 있습니다.")

    init_tickers()
    logger.info("=== 24/7 stock watcher started ===")

    while True:
        now = datetime.now()
        maybe_send_topn(now)

        if combined:
            start = cursor
            end = min(cursor + BATCH_SIZE, len(combined))
            batch = combined[start:end]
            cursor = 0 if end >= len(combined) else end

            logger.info(f"Scan batch {start} ~ {end} / {len(combined)}")
            for index_name, symbol in batch:
                check_symbol_and_alert(index_name, symbol, now)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    # 로컬에서만 실행 (GitHub Actions는 cloud_scan_once.py 로 진입)
    main()
