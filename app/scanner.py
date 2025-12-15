# app/scanner.py
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
import yfinance as yf

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX = "https://en.wikipedia.org/wiki/Nasdaq-100"

# -----------------------------
# Universe (S&P500 + NASDAQ100)
# -----------------------------

@dataclass(frozen=True)
class UniverseItem:
    index_name: str
    symbol: str
    name: str
    sector: str  # 산업군/섹터(위키 GICS Sector)
    sub_industry: str = ""


def _read_html_tables(url: str) -> List[pd.DataFrame]:
    # wikipedia는 가끔 requests 막힐 수 있어 User-Agent 넣음
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).text
    return pd.read_html(html)


def load_sp500_universe() -> List[UniverseItem]:
    tables = _read_html_tables(WIKI_SP500)
    # 첫 테이블이 구성종목 표인 경우가 대부분
    df = tables[0].copy()
    # 컬럼명: Symbol, Security, GICS Sector, GICS Sub-Industry ...
    items: List[UniverseItem] = []
    for _, r in df.iterrows():
        sym = str(r.get("Symbol", "")).strip()
        name = str(r.get("Security", "")).strip()
        sector = str(r.get("GICS Sector", "")).strip()
        sub = str(r.get("GICS Sub-Industry", "")).strip()
        if sym:
            # 일부 티커(BRK.B 등) yfinance 형식 변환
            sym = sym.replace(".", "-")
            items.append(UniverseItem("S&P500", sym, name, sector, sub))
    return items


def load_nasdaq100_universe() -> List[UniverseItem]:
    tables = _read_html_tables(WIKI_NDX)

    # 나스닥100은 표가 여러개라 "Ticker" 컬럼 포함된 표를 찾는다
    target = None
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any("ticker" in c for c in cols) and any("company" in c for c in cols):
            target = t.copy()
            break
    if target is None:
        return []

    # 컬럼 후보: Ticker / Company / GICS Sector / GICS Sub-Industry
    # 위키 페이지 개정에 대비해서 유연하게 가져옴
    def pick(colnames: List[str]) -> Optional[str]:
        cols = {str(c).strip(): c for c in target.columns}
        for want in colnames:
            for k in cols:
                if want.lower() == str(k).strip().lower():
                    return cols[k]
        # 부분일치
        for want in colnames:
            for k in cols:
                if want.lower() in str(k).lower():
                    return cols[k]
        return None

    c_ticker = pick(["Ticker", "Symbol"])
    c_company = pick(["Company", "Security"])
    c_sector = pick(["GICS Sector", "Sector"])
    c_sub = pick(["GICS Sub-Industry", "Sub-Industry", "Industry"])

    items: List[UniverseItem] = []
    for _, r in target.iterrows():
        sym = str(r.get(c_ticker, "")).strip() if c_ticker else ""
        name = str(r.get(c_company, "")).strip() if c_company else ""
        sector = str(r.get(c_sector, "")).strip() if c_sector else "NASDAQ100"
        sub = str(r.get(c_sub, "")).strip() if c_sub else ""
        if sym:
            sym = sym.replace(".", "-")
            items.append(UniverseItem("NASDAQ100", sym, name, sector, sub))
    return items


def load_universe() -> List[UniverseItem]:
    sp = load_sp500_universe()
    ndx = load_nasdaq100_universe()

    # 중복 티커(두 지수에 같이 있을 수 있음) 제거: S&P500 우선
    seen = set()
    out: List[UniverseItem] = []
    for it in sp + ndx:
        if it.symbol in seen:
            continue
        seen.add(it.symbol)
        out.append(it)
    return out


# -----------------------------
# Price download (Daily)
# -----------------------------

def load_price_daily(symbol: str, period: str = "180d") -> Optional[pd.DataFrame]:
    """
    일봉 데이터 (UTC timestamp지만 Date index로 처리)
    """
    try:
        df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
        if df is None or df.empty:
            return None
        df = df.dropna().copy()
        # 날짜 인덱스 표준화
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception:
        return None


# -----------------------------
# Indicators
# -----------------------------

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # MA
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["MA120"] = df["Close"].rolling(120).mean()

    # Bollinger (20, 2)
    mid = df["MA20"]
    std = df["Close"].rolling(20).std()
    df["Upper"] = mid + 2 * std
    df["Lower"] = mid - 2 * std

    # MFI(14)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    rmf = tp * df["Volume"]
    direction = tp.diff()

    pos = rmf.where(direction > 0, 0.0)
    neg = rmf.where(direction < 0, 0.0).abs()

    pos_sum = pos.rolling(14).sum()
    neg_sum = neg.rolling(14).sum()
    mfr = pos_sum / (neg_sum.replace(0, 1e-9))
    df["MFI"] = 100 - (100 / (1 + mfr))

    # Volume MA20
    df["VolMA20"] = df["Volume"].rolling(20).mean()

    return df


# -----------------------------
# Conditions (당신 조건)
# -----------------------------

def evaluate_conditions(df: pd.DataFrame) -> Dict[str, bool]:
    """
    여기서 trigger 조건을 '볼린저 하단 터치 후 반등' 중심으로 둡니다.
    필요하면 다른 조건을 더 켜면 됩니다.
    """
    if df is None or len(df) < 25:
        return {"trigger": False, "bollinger_rebound": False, "mfi_strong": False, "volume_strong": False}

    d = df.iloc[-1]
    prev = df.iloc[-2]

    # ✅ 볼린저 하단 터치 후 반등:
    # - 전일 종가 <= 전일 Lower
    # - 금일 종가 > 금일 Lower AND 금일 종가 > 전일 종가
    bollinger_rebound = (prev["Close"] <= prev["Lower"]) and (d["Close"] > d["Lower"]) and (d["Close"] > prev["Close"])

    # 보조 조건 (원하면 trigger에 포함)
    mfi_strong = bool(d.get("MFI", 0) >= 50)
    volume_strong = bool(d.get("Volume", 0) >= (d.get("VolMA20", 0) if pd.notna(d.get("VolMA20", 0)) else 0))

    trigger = bollinger_rebound  # 기본은 이 조건만

    return {
        "trigger": bool(trigger),
        "bollinger_rebound": bool(bollinger_rebound),
        "mfi_strong": bool(mfi_strong),
        "volume_strong": bool(volume_strong),
    }


# -----------------------------
# Market cap (only for candidates)
# -----------------------------

def get_market_cap(symbol: str) -> int:
    """
    후보 종목만 호출하므로 느려도 OK.
    fast_info 우선 -> 없으면 info fallback
    """
    try:
        t = yf.Ticker(symbol)
        fi = getattr(t, "fast_info", None)
        if fi:
            # yfinance 버전에 따라 key가 다를 수 있어 유연하게
            for k in ("marketCap", "market_cap", "mktCap", "market_capitalization"):
                v = fi.get(k) if isinstance(fi, dict) else None
                if isinstance(v, (int, float)) and v > 0:
                    return int(v)
        info = t.info or {}
        v = info.get("marketCap")
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
    except Exception:
        pass
    return 0


def get_company_name(symbol: str, fallback: str = "") -> str:
    # 위키 이름이 비어있거나 줄이고 싶을 때 사용
    if fallback:
        return fallback
    try:
        info = yf.Ticker(symbol).info or {}
        return str(info.get("shortName") or info.get("longName") or symbol)
    except Exception:
        return symbol


# -----------------------------
# Daily "sent" state (avoid duplicates across 08/12/22)
# -----------------------------

def load_sent_state(path: str) -> Tuple[str, List[str]]:
    """
    return (YYYY-MM-DD, sent_symbols)
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return str(obj.get("date", "")), list(obj.get("sent", []))
    except Exception:
        return "", []


def save_sent_state(path: str, d: str, sent: List[str]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"date": d, "sent": sent}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
