# app/universe.py
import pandas as pd

# =========================
# 지수별 종목 자동 수집
# =========================

def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    return df[["Symbol", "Security"]]


def get_nasdaq100():
    url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    df = pd.read_html(url)[4]
    return df[["Ticker", "Company"]].rename(
        columns={"Ticker": "Symbol", "Company": "Security"}
    )


def get_dowjones():
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    df = pd.read_html(url)[1]
    return df[["Symbol", "Company"]].rename(
        columns={"Company": "Security"}
    )


# =========================
# 테마 분류 규칙
# =========================

THEME_KEYWORDS = {
    "반도체": ["Semiconductor", "Chip", "NVIDIA", "AMD", "Intel", "TSMC"],
    "AI": ["AI", "Artificial", "Cloud", "Data", "Microsoft", "Alphabet", "Meta"],
    "금/은/원자재": ["Gold", "Silver", "Mining", "Commodity", "Materials"],
}


def classify_theme(company_name: str) -> str:
    name = company_name.lower()
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name:
                return theme
    return "기타"
