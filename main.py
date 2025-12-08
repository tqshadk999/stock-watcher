# main.py  — 24시간 감시 + 텔레그램 알림
# - 조건 만족 시: Price+MFI 차트 1장 + Volume 차트 1장 텔레그램 전송
# - 조건 검사는 60일 1시간봉(df_1h)
# - 세 그래프(Price, MFI, Volume) 모두
#   "오늘 기준 최근 60 영업일(일봉 종가 기준)" x축을 동일하게 사용 (MM-DD 라벨)

import os
import time
import logging
from datetime import datetime, date
from io import BytesIO

import numpy as np
import mplfinance as mpf  # Volume 쪽에는 그대로 사용
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.patches import Rectangle
from dotenv import load_dotenv
import yfinance as yf  # 회사 이름 조회용

from notifier import send_message, send_photo
from utils import (
    get_sp500_tickers,
    get_nasdaq100_tickers,
    safe_download_symbol,
    add_indicators,         # 1시간봉 조건 계산용 (그대로 둠)
    evaluate_conditions,
    top_n_by_marketcap,
)

# ─────────────────────────────────────
# 환경 변수 로드 (.env)
# ─────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))  # 감시 루프 간격(초)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "30"))                  # 한 번에 검사할 종목 수
TOPN = int(os.getenv("TOPN", "10"))                              # 추천 종목 개수

# 하루 중 추천 보내는 시각 (PC 로컬 시간 기준, HH:MM)
TOPN_TIMES = ["08:00", "13:00", "22:00"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scanner] %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# 전역 데이터
# ─────────────────────────────────────
sp500_tickers: list[str] = []
nasdaq_tickers: list[str] = []
combined: list[tuple[str, str]] = []  # (index_name, symbol)

cursor: int = 0  # 다음에 검사할 인덱스
last_alert_time: dict[tuple[str, str], datetime] = {}  # (index, symbol) -> 마지막 알림 시간
last_topn_sent: dict[tuple[str, str], date] = {}       # (index, HH:MM) -> 마지막 발송 날짜


# ─────────────────────────────────────
# 회사 이름 가져오기 (티커 -> 풀네임)
# ─────────────────────────────────────
def get_company_name(symbol: str) -> str:
    """
    yfinance에서 회사 이름을 가져온다.
    실패하면 빈 문자열 반환.
    """
    try:
        t = yf.Ticker(symbol)
        info = t.info
        return info.get("shortName") or info.get("longName") or ""
    except Exception:
        return ""


# ─────────────────────────────────────
# 공통: 1시간봉 → 일봉(180일) 지표 계산 → 최근 60 영업일만 사용
# ─────────────────────────────────────
def make_daily_60(df_1h: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    차트에 사용할 '오늘 기준 최근 60 영업일' 데이터프레임 생성.
    - 지표 계산은 180일 일봉으로 넉넉하게 하고
    - 마지막 60 영업일만 잘라서 차트에 사용
    - 인덱스는 '날짜만' (시간 00:00:00 제거)
    """
    # 1) 가능하면 yfinance 일봉(180d) 사용
    df_daily_long = safe_download_symbol(symbol, period="180d", interval="1d")
    if df_daily_long is None or df_daily_long.empty:
        # 2) 백업: 1시간봉 → 일봉 리샘플링
        df_daily_long = (
            df_1h.resample("1D")
            .agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
            .dropna(subset=["Open", "High", "Low", "Close"])
        )

    df_daily_long = df_daily_long.sort_index().copy()

    # ── 3) 일봉 지표 직접 계산 (Price/MFI/Volume 용) ──

    # 이동평균 20 / 60 / 120
    for n in (20, 60, 120):
        df_daily_long[f"MA{n}"] = df_daily_long["Close"].rolling(n).mean()

    # 볼린저 밴드 (20일, 2표준편차)
    ma20 = df_daily_long["Close"].rolling(20).mean()
    std20 = df_daily_long["Close"].rolling(20).std()
    df_daily_long["Upper"] = ma20 + 2 * std20
    df_daily_long["Lower"] = ma20 - 2 * std20

    # 거래량 20일 평균
    df_daily_long["VolMA20"] = df_daily_long["Volume"].rolling(20).mean()

    # MFI(14)
    tp = (df_daily_long["High"] + df_daily_long["Low"] + df_daily_long["Close"]) / 3
    mf = tp * df_daily_long["Volume"]

    pmf = [0.0]
    nmf = [0.0]
    for i in range(1, len(df_daily_long)):
        if tp.iloc[i] > tp.iloc[i - 1]:
            pmf.append(mf.iloc[i])
            nmf.append(0.0)
        elif tp.iloc[i] < tp.iloc[i - 1]:
            pmf.append(0.0)
            nmf.append(mf.iloc[i])
        else:
            pmf.append(0.0)
            nmf.append(0.0)

    df_daily_long["PMF"] = pmf
    df_daily_long["NMF"] = nmf

    period = 14
    pmf_sum = df_daily_long["PMF"].rolling(period).sum()
    nmf_sum = df_daily_long["NMF"].rolling(period).sum()

    mfr = pmf_sum / nmf_sum.replace(0, np.nan)
    df_daily_long["MFI"] = 100 - (100 / (1 + mfr))

    # ── 4) 최근 60 영업일만 사용 ──
    df_daily = df_daily_long.tail(60).copy()
    if df_daily.empty:
        df_daily = df_daily_long.copy()

    # 인덱스를 '날짜만'으로 정규화
    df_daily.index = pd.to_datetime(df_daily.index.date)

    return df_daily


# ─────────────────────────────────────
# Price + MFI 차트 (일봉 종가 기준 최근 60 영업일) — 직접 그림
# ─────────────────────────────────────
def build_price_mfi_chart(df_daily: pd.DataFrame, symbol: str, index_name: str) -> bytes:
    """
    - 위: 캔들 + MA20/60/120 + 볼린저 밴드(노란선)
    - 아래: MFI (80/20 기준선)
    - x축: 오늘 기준 최근 60 영업일 (MM-DD)
    """

    df = df_daily.copy()
    dates = mdates.date2num(df.index.to_pydatetime())

    fig = plt.figure(figsize=(11, 7))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    # ── 캔들 ──
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
        height = body_top - body_bottom
        if height == 0:
            height = 0.001  # 가격 변동 없는 날

        ax1.add_patch(
            Rectangle(
                (x - candle_width / 2.0, body_bottom),
                candle_width,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.5,
                zorder=3,
            )
        )

    # ── 이평선 ──
    if "MA20" in df:
        ax1.plot(dates, df["MA20"], color="limegreen", label="MA20", linewidth=1)
    if "MA60" in df:
        ax1.plot(dates, df["MA60"], color="orange", label="MA60", linewidth=1)
    if "MA120" in df:
        ax1.plot(dates, df["MA120"], color="purple", label="MA120", linewidth=1)

    # ── 볼린저 밴드 ──
    if "Upper" in df and "Lower" in df:
        ax1.plot(dates, df["Upper"], color="gold", linestyle="--", linewidth=0.9, label="Upper")
        ax1.plot(dates, df["Lower"], color="gold", linestyle="--", linewidth=0.9, label="Lower")

    ax1.set_title(f"{index_name} / {symbol}")
    ax1.set_ylabel("Price")
    ax1.legend(loc="upper left", fontsize=8)

    # ── MFI ──
    if "MFI" in df:
        ax2.plot(dates, df["MFI"], color="purple", linewidth=1.5, label="MFI")
    ax2.axhline(80, color="red", linestyle="--", linewidth=0.8)
    ax2.axhline(20, color="green", linestyle="--", linewidth=0.8)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("MFI")
    ax2.legend(loc="upper left", fontsize=8)

    # ── x축: 최근 60 영업일, MM-DD ──
    xmin = df.index.min()
    xmax = df.index.max()
    locator = mdates.DayLocator(interval=5)
    formatter = mdates.DateFormatter("%m-%d")

    for ax in (ax1, ax2):
        ax.set_xlim(xmin, xmax)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────
# Volume 전용 차트 (일봉 종가 기준 최근 60 영업일)
# ─────────────────────────────────────
def build_volume_chart(df_daily: pd.DataFrame, symbol: str, index_name: str) -> bytes:
    """
    Volume 전용 1패널 차트 (일봉 기준)
    - 입력 df_daily: make_daily_60()에서 만든 60 영업일 데이터
    - 막대: 전부 검은색
    - 20일 거래량 평균 노란선
    - y축: 10.0M / 10.5K
    - x축: 날짜만 (MM-DD) — Price/MFI와 완전히 동일
    """

    # 20일 거래량 평균 (혹시 없으면 계산)
    if "VolMA20" not in df_daily.columns:
        df_daily["VolMA20"] = df_daily["Volume"].rolling(window=20).mean()

    dates = mdates.date2num(df_daily.index.to_pydatetime())

    fig, ax = plt.subplots(figsize=(10, 4))

    vol_mask = df_daily["Volume"] > 0

    # 막대 거래량 — 전부 검은색
    ax.bar(
        dates[vol_mask],
        df_daily["Volume"][vol_mask],
        width=0.6,
        color="black",
        align="center",
        label="Volume",
    )

    # 20일 평균선
    ax.plot(
        dates,
        df_daily["VolMA20"],
        color="yellow",
        linewidth=1.5,
        label="Vol MA20",
    )

    ax.set_title(f"{index_name} / {symbol} - Volume (Daily 60)")
    ax.set_ylabel("Volume")
    ax.legend(loc="upper left", fontsize=8)

    # y축: 10.0M / 10.5K
    ax.ticklabel_format(style="plain", axis="y")

    def vol_formatter(x, pos):
        x = float(x)
        if x >= 1_000_000:
            return f"{x/1_000_000:.1f}M"
        elif x >= 1_000:
            return f"{x/1_000:.1f}K"
        else:
            return str(int(x))

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(vol_formatter))

    # ✅ x축: Price/MFI와 동일한 범위 + 포맷
    xmin = df_daily.index.min()
    xmax = df_daily.index.max()

    locator = mdates.DayLocator(interval=5)
    formatter = mdates.DateFormatter("%m-%d")
    ax.set_xlim(xmin, xmax)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.autofmt_xdate()

    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────
# 티커 로딩
# ─────────────────────────────────────
def init_tickers():
    global sp500_tickers, nasdaq_tickers, combined
    sp500_tickers = get_sp500_tickers()
    nasdaq_tickers = get_nasdaq100_tickers()
    combined = [("S&P500", s) for s in sp500_tickers] + [("NASDAQ100", s) for s in nasdaq_tickers]
    logger.info(f"Loaded {len(sp500_tickers)} S&P500, {len(nasdaq_tickers)} NASDAQ100 tickers")


# ─────────────────────────────────────
# 단일 종목 조건 검사 + 알림
# ─────────────────────────────────────
def check_symbol_and_alert(index_name: str, symbol: str, now: datetime):
    try:
        # 1시간봉 60일 데이터 (조건 검사용)
        df_1h = safe_download_symbol(symbol, period="60d", interval="1h")
        if df_1h is None or df_1h.empty:
            return

        df_1h = add_indicators(df_1h)
        conds = evaluate_conditions(df_1h)
        if not conds["trigger"]:
            return

        # ───── 공통: 일봉 기준 최근 60 영업일 데이터 생성 ─────
        df_daily_60 = make_daily_60(df_1h, symbol)

        # 스팸 방지: 2시간 이내 같은 종목/지수 알림 금지
        key = (index_name, symbol)
        last_time = last_alert_time.get(key)
        if last_time and (now - last_time).total_seconds() < 7200:
            return

        # ───────── 시가 / 종가 / 현재가 계산 ─────────
        day_open = day_close = current_price = None
        try:
            today = now.date()
            df_today = df_1h[df_1h.index.date == today]

            # 오늘 데이터 없으면 마지막 거래일 기준
            if df_today.empty:
                last_day = df_1h.index[-1].date()
                df_today = df_1h[df_1h.index.date == last_day]

            if not df_today.empty:
                day_open = float(df_today["Open"].iloc[0])
                day_close = float(df_today["Close"].iloc[-1])

            current_price = float(df_1h["Close"].iloc[-1])
        except Exception:
            day_open = day_close = current_price = None

        # 회사 이름
        company_name = get_company_name(symbol)
        display_name = f"{symbol} {company_name}" if company_name else symbol

        # 텍스트 메시지 구성
        text_lines = [f"*{index_name} / {display_name}*"]
        if conds["bollinger_rebound"]:
            text_lines.append("• 볼린저 밴드 하단 터치 후 반등")
        if conds["breakout_90d"]:
            text_lines.append("• 최근 90일 신고가 돌파")
        if conds["mfi_strong"]:
            text_lines.append("• MFI 강세 (50 이상)")
        if conds["volume_strong"]:
            text_lines.append("• 거래량 20MA 상회")

        if day_open is not None:
            text_lines.append(
                f"\n시가: {day_open:,.2f} / 종가: {day_close:,.2f} / 현재가: {current_price:,.2f}"
            )

        text_lines.append(f"\n시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        caption = "\n".join(text_lines)

        # 1) Price + MFI 차트
        chart_bytes = build_price_mfi_chart(df_daily_60, symbol, index_name)
        send_photo(TELEGRAM_TOKEN, CHAT_ID, chart_bytes, caption=caption, parse_mode="Markdown")
        time.sleep(0.8)

        # 2) Volume 차트
        vol_bytes = build_volume_chart(df_daily_60, symbol, index_name)
        send_photo(TELEGRAM_TOKEN, CHAT_ID, vol_bytes, caption=caption + "\n(📊 거래량)", parse_mode="Markdown")

        last_alert_time[key] = now
        time.sleep(0.8)  # 텔레그램 과다 요청 방지
    except Exception as e:
        logger.warning(f"Error processing {index_name} {symbol}: {e}")


# ─────────────────────────────────────
# 특정 시각에 TopN 추천 보내기
# ─────────────────────────────────────
def maybe_send_topn(now: datetime):
    today = now.date()
    current_hm = now.strftime("%H:%M")

    if current_hm not in TOPN_TIMES:
        return

    for index_name in ["S&P500", "NASDAQ100"]:
        key = (index_name, current_hm)
        if last_topn_sent.get(key) == today:
            # 이미 오늘 이 시간에 보냈음
            continue

        logger.info(f"Sending Top{TOPN} for {index_name} at {current_hm}")
        symbols = get_sp500_tickers() if index_name == "S&P500" else get_nasdaq100_tickers()

        matched = []
        for s in symbols:
            try:
                df_d = safe_download_symbol(s, period="120d", interval="1d")
                if df_d is None or df_d.empty:
                    continue
                df_d = add_indicators(df_d)
                conds = evaluate_conditions(df_d)
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


# ─────────────────────────────────────
# 메인 루프 (24/7 감시)
# ─────────────────────────────────────
def main():
    global cursor

    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError(".env의 TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다.")

    init_tickers()
    logger.info("=== 24/7 stock watcher started ===")

    while True:
        now = datetime.now()  # 로컬 PC 시간 기준

        # 1) 정해진 시각에 TopN 추천
        maybe_send_topn(now)

        # 2) 실시간 조건 감시 — 매 루프마다 BATCH_SIZE개 종목 검사
        if combined:
            start = cursor
            end = min(cursor + BATCH_SIZE, len(combined))
            batch = combined[start:end]
            cursor = 0 if end >= len(combined) else end

            logger.info(f"Scan batch {start} ~ {end} / {len(combined)}")

            for index_name, symbol in batch:
                check_symbol_and_alert(index_name, symbol, now)

        # 3) 잠시 대기 후 반복
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
