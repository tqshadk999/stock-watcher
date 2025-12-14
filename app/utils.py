# utils.py
import time
import logging
from io import BytesIO

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf

logger = logging.getLogger(__name__)


# ----------------- 티커 리스트 -----------------
def get_sp500_tickers() -> list[str]:
    """S&P500 티커 리스트"""
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500/master/data/constituents.csv"
        df = pd.read_csv(url)
        return df["Symbol"].astype(str).str.strip().tolist()
    except Exception:
        # 위가 실패하면 위키백과로 fallback
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"class": "wikitable"})
        tickers = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if cols:
                tickers.append(cols[0].text.strip())
        return tickers


def get_nasdaq100_tickers() -> list[str]:
    """NASDAQ100 티커 리스트"""
    try:
        url = "https://raw.githubusercontent.com/robertomurray/nasdaq-list/master/nasdaq-100.csv"
        df = pd.read_csv(url)
        for col in ["Symbol", "Ticker", "symbols"]:
            if col in df.columns:
                return df[col].astype(str).str.strip().tolist()
        return df.iloc[:, 0].astype(str).str.strip().tolist()
    except Exception:
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"class": "wikitable"})
        tickers = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) > 1:
                tickers.append(cols[1].text.strip())
        return tickers


# ----------------- yfinance 다운로드 -----------------
def normalize_df(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        # 단일 심볼이 아닌 경우가 들어왔다면 droplevel 시도
        try:
            df = df.droplevel(1, axis=1)
        except Exception:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    # 컬럼명 정리
    rename = {}
    for c in df.columns:
        s = str(c)
        if s.lower().startswith("adj"):
            rename[c] = "Adj Close"
        elif s in ["Open", "High", "Low", "Close", "Volume", "Adj Close"]:
            rename[c] = s
        else:
            rename[c] = s
    return df.rename(columns=rename)


def safe_download_symbol(
    symbol: str,
    period: str = "120d",
    interval: str = "1h",
    retries: int = 3,
    pause: float = 1.0,
) -> pd.DataFrame | None:
    symbol = symbol.strip().upper()
    for i in range(retries):
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is None or df.empty:
                time.sleep(pause)
                continue
            df = normalize_df(df)
            return df
        except Exception as e:
            logger.warning(f"yf download failed {symbol} attempt {i+1}: {e}")
            time.sleep(pause * (i + 1))
    return None


# ----------------- 지표 계산 -----------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["Close", "High", "Low", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Volume"] = df["Volume"].fillna(0)

    # 이평선
    df["MA5"] = df["Close"].rolling(5, min_periods=1).mean()
    df["MA20"] = df["Close"].rolling(20, min_periods=1).mean()
    df["MA60"] = df["Close"].rolling(60, min_periods=1).mean()
    df["MA120"] = df["Close"].rolling(120, min_periods=1).mean()

    # 볼린저 밴드
    df["STD20"] = df["Close"].rolling(20, min_periods=1).std()
    df["Upper"] = df["MA20"] + 2 * df["STD20"]
    df["Lower"] = df["MA20"] - 2 * df["STD20"]

    # MFI
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = typical * df["Volume"]
    pos = mf.where(typical > typical.shift(1), 0.0)
    neg = mf.where(typical < typical.shift(1), 0.0)
    pos_sum = pos.rolling(14).sum()
    neg_sum = neg.rolling(14).sum().replace(0, 1e-9)
    mfr = pos_sum / neg_sum
    df["MFI"] = 100 - (100 / (1 + mfr))

    # 90일 신고가
    df["Highest90"] = df["Close"].rolling(90, min_periods=1).max()

    return df


# ----------------- 조건 체크 -----------------
def evaluate_conditions(df: pd.DataFrame) -> dict:
    """
    볼린저 하단 반등, 신고가 돌파, MFI, 거래량 조건 평가
    trigger: 알림을 보낼지 여부
    """
    if df is None or len(df) < 25:
        return {"trigger": False}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 볼린저 하단 터치 후 반등
    cond_boll = bool(prev["Close"] <= prev["Lower"] and last["Close"] > last["Lower"])

    # 90일 신고가 돌파
    prior_high = df["Highest90"].shift(1).iloc[-1]
    cond_break = bool(last["Close"] > prior_high)

    # MFI & 거래량 (보조 신호)
    vol_ma20 = df["Volume"].rolling(20).mean().iloc[-1]
    cond_mfi = bool(last["MFI"] > 50)
    cond_vol = bool(last["Volume"] > vol_ma20)

    trigger = cond_boll or cond_break  # 주 트리거: 볼린저 반등 또는 신고가
    return {
        "trigger": trigger,
        "bollinger_rebound": cond_boll,
        "breakout_90d": cond_break,
        "mfi_strong": cond_mfi,
        "volume_strong": cond_vol,
    }


# ----------------- 시가총액 계산 & Top N -----------------
def market_cap_of(symbol: str) -> int:
    symbol = symbol.strip().upper()
    try:
        t = yf.Ticker(symbol)
        info = t.info
        mc = info.get("marketCap") or info.get("market_cap") or 0
        if not mc and info.get("sharesOutstanding"):
            df = safe_download_symbol(symbol, period="5d", interval="1d")
            if df is not None and not df.empty:
                last = float(df["Close"].iloc[-1])
                mc = int(last * info.get("sharesOutstanding", 0))
        return int(mc or 0)
    except Exception as e:
        logger.debug(f"market cap fetch err {symbol}: {e}")
        return 0


def top_n_by_marketcap(symbols: list[str], n: int = 10) -> list[str]:
    pairs = []
    for s in symbols:
        mc = market_cap_of(s)
        pairs.append((s, mc))
        time.sleep(0.2)  # API 속도/제한 고려
    pairs_sorted = sorted(pairs, key=lambda x: x[1] or 0, reverse=True)
    return [s for s, _ in pairs_sorted[:n]]
