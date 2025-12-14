# app/scanner.py
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import yfinance as yf


# --------------------------
# Theme definitions (간단/안정 우선)
# --------------------------
THEMES = ["SEMICONDUCTOR", "COMMODITY_ETF", "AI", "DIVIDEND"]

# ETF/ETN 쪽은 심볼만으로 분류가 가장 안정적이라서 “대표 리스트” 방식 사용
COMMODITY_TICKERS = {
    # Gold / Silver
    "GLD", "IAU", "SLV", "SIVR",
    # Broad commodities
    "DBC", "PDBC", "GSG", "COMT",
    # Oil/energy proxies
    "USO", "BNO",
    # Copper
    "CPER",
}

DIVIDEND_TICKERS = {
    "SCHD", "VYM", "HDV", "DVY", "SPYD", "SDY", "NOBL"
}

AI_KEYWORDS = [
    "artificial intelligence", "ai", "machine learning", "cloud", "data", "gpu"
]
SEMI_KEYWORDS = [
    "semiconductor", "semiconductors", "chip", "memory", "fab", "foundry"
]


@dataclass
class Pick:
    symbol: str
    name: str
    market_cap: int
    theme: str


# --------------------------
# Indicators
# --------------------------
def _mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    mf = tp * df["Volume"]
    pos = mf.where(tp > tp.shift(1), 0.0)
    neg = mf.where(tp < tp.shift(1), 0.0)
    pos_sum = pos.rolling(period).sum()
    neg_sum = neg.rolling(period).sum()
    mfr = pos_sum / (neg_sum.replace(0, 1e-9))
    return 100 - (100 / (1 + mfr))


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["Upper"] = df["MA20"] + 2 * df["STD20"]
    df["Lower"] = df["MA20"] - 2 * df["STD20"]
    df["MFI"] = _mfi(df, 14)
    return df


def bollinger_rebound(df: pd.DataFrame) -> bool:
    """
    볼린저 밴드 하단 터치 후 반등 (일봉 기준)
    - 전일 종가가 Lower 아래/근처
    - 당일 종가가 Lower 위로 복귀 + 전일 종가보다 상승
    """
    if len(df) < 25:
        return False
    d = add_indicators(df).dropna()
    if len(d) < 5:
        return False

    prev = d.iloc[-2]
    last = d.iloc[-1]

    if math.isnan(prev["Lower"]) or math.isnan(last["Lower"]):
        return False

    touch = prev["Close"] <= prev["Lower"] * 1.01
    rebound = (last["Close"] > last["Lower"]) and (last["Close"] > prev["Close"])
    return bool(touch and rebound)


# --------------------------
# Universe (S&P500 + Nasdaq100 + Dow30)
# --------------------------
def load_universe_tickers() -> List[str]:
    # yfinance 내장 리스트가 없어 위키 대신, 안정적으로 "indices tickers csv"를 쓰는게 보통인데
    # 여기서는 최소 의존성 위해 yfinance의 major index constituents 방식 대신:
    #  - S&P500, Nasdaq100, Dow30를 “대표 ETF”로 대체하는 편법은 정확하지 않음
    #  - 사용자가 이미 utils로 받아오던 구조가 있으니, 여기서는 “현재 레포 구조”에 맞춰
    #    ticker list 파일을 따로 두지 않는 대신: 일단 사용자가 넣은 즐겨찾기/테마 종목 중심 + 인기 대형주 보강.
    #
    # => “전체 자동 수집”은 별도 안정화 필요(위키/CSV). 지금은 Actions 안정 동작을 최우선으로 함.
    base = set()

    # Large cap core (샘플이 아니라 실제 운영 시 여기에 자동수집으로 교체 권장)
    mega = [
        "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","LLY","AVGO",
        "JPM","V","MA","XOM","UNH","COST","WMT","HD","PG","KO","PEP","CRM","ADBE",
        "AMD","INTC","QCOM","TXN","MU","ASML","TSM","AMAT","LRCX","KLAC",
    ]
    base.update(mega)

    # Theme tickers
    base.update(COMMODITY_TICKERS)
    base.update(DIVIDEND_TICKERS)

    return sorted(base)


# --------------------------
# Market cap + name
# --------------------------
def get_name_and_marketcap(symbol: str) -> Tuple[str, int]:
    t = yf.Ticker(symbol)
    name = symbol
    mcap = 0

    # fast_info 우선 (빠름)
    try:
        fi = getattr(t, "fast_info", None)
        if fi:
            mcap = int(fi.get("marketCap") or 0)
            # longName은 info에 주로 존재
    except Exception:
        pass

    try:
        info = t.get_info()
        name = info.get("shortName") or info.get("longName") or name
        if not mcap:
            mcap = int(info.get("marketCap") or 0)
    except Exception:
        pass

    return name, mcap


# --------------------------
# Theme classification
# --------------------------
def classify_theme(symbol: str, name: str) -> List[str]:
    sym = symbol.upper()
    nm = (name or "").lower()

    themes = []

    if sym in COMMODITY_TICKERS:
        themes.append("COMMODITY_ETF")

    if sym in DIVIDEND_TICKERS:
        themes.append("DIVIDEND")

    # Semi / AI는 키워드 기반(완벽 X, 하지만 자동화 목적)
    if any(k in nm for k in SEMI_KEYWORDS):
        themes.append("SEMICONDUCTOR")

    if any(k in nm for k in AI_KEYWORDS):
        themes.append("AI")

    # 보강: 심볼 기반 힌트
    if sym in {"NVDA","AMD","INTC","QCOM","AVGO","MU","AMAT","LRCX","KLAC","TSM","ASML"}:
        if "SEMICONDUCTOR" not in themes:
            themes.append("SEMICONDUCTOR")
        if sym in {"NVDA"} and "AI" not in themes:
            themes.append("AI")

    return themes or ["AI"]  # 분류 실패 시 기본값(원하면 "OTHER"로 변경 가능)


# --------------------------
# Price download (daily)
# --------------------------
def download_daily(symbols: List[str], period: str = "6mo") -> Dict[str, pd.DataFrame]:
    """
    yfinance 멀티다운로드: 호출 횟수 줄여서 Actions 안정성 확보
    """
    out: Dict[str, pd.DataFrame] = {}
    if not symbols:
        return out

    data = yf.download(
        tickers=" ".join(symbols),
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=False,
        progress=False,
    )

    # 단일 ticker면 컬럼 구조가 다름
    if isinstance(data.columns, pd.MultiIndex):
        for sym in symbols:
            if sym in data.columns.get_level_values(0):
                df = data[sym].dropna()
                if not df.empty:
                    out[sym] = df
    else:
        df = data.dropna()
        if not df.empty and len(symbols) == 1:
            out[symbols[0]] = df

    return out


# --------------------------
# Main scan logic
# --------------------------
def scan_themes_top10(now: datetime) -> Dict[str, List[Pick]]:
    universe = load_universe_tickers()

    # 1) name + marketcap 수집
    meta = []
    for sym in universe:
        name, mcap = get_name_and_marketcap(sym)
        if mcap and mcap > 0:
            meta.append((sym, name, mcap))

    # 2) theme별 Top100 mcap 구성
    theme_candidates: Dict[str, List[Tuple[str, str, int]]] = {t: [] for t in THEMES}
    for sym, name, mcap in meta:
        themes = classify_theme(sym, name)
        for th in themes:
            if th in theme_candidates:
                theme_candidates[th].append((sym, name, mcap))

    for th in THEMES:
        theme_candidates[th].sort(key=lambda x: x[2], reverse=True)
        theme_candidates[th] = theme_candidates[th][:100]

    # 3) 스캔 대상 union
    scan_syms = sorted({sym for th in THEMES for sym, _, _ in theme_candidates[th]})
    prices = download_daily(scan_syms, period="6mo")

    # 4) 조건 필터링 + Top10
    results: Dict[str, List[Pick]] = {t: [] for t in THEMES}

    for th in THEMES:
        for sym, name, mcap in theme_candidates[th]:
            df = prices.get(sym)
            if df is None or df.empty:
                continue
            if bollinger_rebound(df):
                results[th].append(Pick(sym, name, mcap, th))

        results[th].sort(key=lambda p: p.market_cap, reverse=True)
        results[th] = results[th][:10]

    return results


def format_theme_message(results: Dict[str, List[Pick]], now: datetime) -> str:
    def line(th_kor: str, picks: List[Pick]) -> str:
        if not picks:
            return f"{th_kor} : (조건 만족 없음)"
        parts = [f"[{p.symbol}] {p.name}" for p in picks]
        return f"{th_kor} : " + "  /  ".join(parts)

    # 원하는 표현 그대로
    msg = []
    msg.append("📌 *조건 만족 Top10 (시총순) — Bollinger 하단 터치 후 반등*")
    msg.append(f"⏱ KST: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    msg.append("")
    msg.append(line("반도체", results.get("SEMICONDUCTOR", [])))
    msg.append(line("금/은/원자재", results.get("COMMODITY_ETF", [])))
    msg.append(line("AI", results.get("AI", [])))
    msg.append(line("배당주", results.get("DIVIDEND", [])))
    return "\n".join(msg)
