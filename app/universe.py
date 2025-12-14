# app/universe.py
from __future__ import annotations

import os
import json
from datetime import date
from typing import Dict, List, Tuple

import requests
import pandas as pd
import yfinance as yf

DATA_DIR = "data"
FUND_CACHE = os.path.join(DATA_DIR, "fundamentals_cache.json")


# -----------------------------
# Wikipedia table fetch (403 방지)
# -----------------------------
def _read_html_tables(url: str) -> List[pd.DataFrame]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; StockWatcher/1.0; +https://github.com/)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return pd.read_html(r.text)


def get_sp500() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = _read_html_tables(url)
    df = tables[0]
    df = df[["Symbol", "Security"]].copy()
    df["Symbol"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False).str.strip()
    df["Security"] = df["Security"].astype(str).str.strip()
    return df


def get_nasdaq100() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    tables = _read_html_tables(url)

    # 'Ticker' 컬럼이 있는 테이블을 찾아서 사용
    target = None
    for t in tables:
        cols = [c.lower() for c in t.columns.astype(str)]
        if "ticker" in cols or "ticker symbol" in cols:
            target = t
            break
        if "ticker" in "".join(cols):
            target = t
            break

    if target is None:
        # 최후 fallback (예전 인덱스)
        target = tables[4]

    # 컬럼 정규화
    cols = list(target.columns.astype(str))
    ticker_col = None
    name_col = None
    for c in cols:
        lc = c.lower()
        if "ticker" in lc:
            ticker_col = c
        if "company" in lc or "security" in lc:
            name_col = c
    if ticker_col is None:
        ticker_col = "Ticker" if "Ticker" in target.columns else target.columns[0]
    if name_col is None:
        name_col = "Company" if "Company" in target.columns else target.columns[1]

    df = target[[ticker_col, name_col]].copy()
    df.columns = ["Symbol", "Security"]
    df["Symbol"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False).str.strip()
    df["Security"] = df["Security"].astype(str).str.strip()
    return df


def get_dowjones() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    tables = _read_html_tables(url)
    # 보통 components 테이블이 1번
    df = tables[1].copy()

    # 컬럼 자동 탐색
    symbol_col = None
    name_col = None
    for c in df.columns.astype(str):
        lc = c.lower()
        if "symbol" in lc or "ticker" in lc:
            symbol_col = c
        if "company" in lc or "security" in lc:
            name_col = c
    if symbol_col is None:
        symbol_col = df.columns[0]
    if name_col is None:
        name_col = df.columns[1]

    out = df[[symbol_col, name_col]].copy()
    out.columns = ["Symbol", "Security"]
    out["Symbol"] = out["Symbol"].astype(str).str.replace(".", "-", regex=False).str.strip()
    out["Security"] = out["Security"].astype(str).str.strip()
    return out


def get_universe() -> pd.DataFrame:
    u = pd.concat([get_sp500(), get_nasdaq100(), get_dowjones()], ignore_index=True)
    u = u.drop_duplicates("Symbol")
    return u


# -----------------------------
# Fundamentals cache (일일 캐시)
# -----------------------------
def _load_cache() -> dict:
    today = date.today().isoformat()
    if not os.path.exists(FUND_CACHE):
        return {"date": today, "items": {}}
    try:
        with open(FUND_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 날짜 다르면 새로
        if data.get("date") != today:
            return {"date": today, "items": {}}
        if "items" not in data:
            data["items"] = {}
        return data
    except Exception:
        return {"date": today, "items": {}}


def _save_cache(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FUND_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _fetch_fundamental(symbol: str) -> dict:
    info = {}
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        info = {}

    return {
        "symbol": symbol,
        "name": (info.get("longName") or info.get("shortName") or "").strip(),
        "sector": (info.get("sector") or "").strip(),
        "industry": (info.get("industry") or "").strip(),
        "marketCap": int(info.get("marketCap") or 0),
        "dividendYield": float(info.get("dividendYield") or 0.0),
    }


def get_fundamentals(symbols: List[str]) -> Dict[str, dict]:
    cache = _load_cache()
    items = cache["items"]  # symbol -> fundamental

    for s in symbols:
        if s not in items:
            items[s] = _fetch_fundamental(s)

    cache["items"] = items
    _save_cache(cache)
    return items


# -----------------------------
# Theme classification (섹터/산업 기반)
# - 한 종목은 "우선순위"로 1개 테마만 부여
# -----------------------------
def classify_theme(f: dict) -> str:
    name = (f.get("name") or "").lower()
    sector = (f.get("sector") or "").lower()
    industry = (f.get("industry") or "").lower()
    dy = float(f.get("dividendYield") or 0.0)

    # 1) 금/은/원자재 (ETF/광산/원자재 섹터)
    if any(k in name for k in ["gold", "silver", "commodity", "oil", "natural gas", "miners", "mining"]) \
       or any(k in industry for k in ["gold", "silver", "oil", "gas", "coal", "copper", "mining", "metals"]) \
       or "basic materials" in sector or "energy" in sector:
        return "금/은/원자재"

    # 2) 반도체
    if "semiconductor" in industry or "semiconductor" in name or "chip" in name:
        return "반도체"

    # 3) AI (소프트웨어/인터넷/클라우드/데이터 중심 산업)
    if any(k in industry for k in ["software", "internet", "data", "semiconductors", "it services"]) \
       or any(k in name for k in ["ai", "artificial intelligence", "cloud", "data", "machine learning"]):
        return "AI"

    # 4) 배당주 (배당수익률 기준, 기본 2% 이상)
    if dy >= 0.02:
        return "배당주"

    return "기타"


# -----------------------------
# 테마별 시총 Top100 뽑기
# -----------------------------
def build_theme_top100() -> Dict[str, List[Tuple[str, str, int]]]:
    """
    return:
      {테마: [(symbol, name, marketCap), ...] }  # 시총 내림차순, 최대 100개
    """
    uni = get_universe()
    symbols = uni["Symbol"].tolist()

    fund = get_fundamentals(symbols)

    buckets: Dict[str, List[Tuple[str, str, int]]] = {"반도체": [], "금/은/원자재": [], "AI": [], "배당주": []}

    for sym in symbols:
        f = fund.get(sym, {})
        mcap = int(f.get("marketCap") or 0)
        if mcap <= 0:
            continue

        theme = classify_theme(f)
        if theme in buckets:
            nm = f.get("name") or uni.loc[uni["Symbol"] == sym, "Security"].iloc[0]
            buckets[theme].append((sym, nm, mcap))

    # 시총순 정렬 후 Top100
    for k in list(buckets.keys()):
        buckets[k].sort(key=lambda x: x[2], reverse=True)
        buckets[k] = buckets[k][:100]

    return buckets
