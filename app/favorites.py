"""
favorites.py
- 개인 즐겨찾기 + S&P500 + NASDAQ100 섹터 통합
- Semiconductor는 세부분류 유지
- FAVORITES 자동 생성
"""

# =====================================================
# 🧠 SEMICONDUCTOR (세부분류 유지 – 최우선 섹터)
# =====================================================

SEMICONDUCTOR = {

    # 🔵 장비 (Equipment)
    "EQUIPMENT": [
        "ASML", "AMAT", "LRCX", "KLAC", "TER",
        "ONTO", "ACLS", "VECO", "MKSI", "ENTG",
        "COHU", "FORM", "AEHR", "NVMI", "UCTT",
    ],

    # 🟢 팹리스 (Fabless)
    "FABLESS": [
        "NVDA", "AMD", "AVGO", "QCOM", "MRVL",
        "NXPI", "ADI", "TXN", "MPWR", "ON",
    ],

    # 🟡 파운드리 (Foundry)
    "FOUNDRY": [
        "TSM", "UMC", "GFS",
    ],

    # 🔴 IDM
    "IDM": [
        "INTC", "MU", "STM", "WDC",
        "IFNNY", "SKM",
    ],
}

# =====================================================
# 🔹 S&P500 + NASDAQ100 공통 산업 섹터
# =====================================================

TECHNOLOGY = [
    "AAPL", "MSFT", "ORCL", "CRM", "ADBE",
    "CSCO", "IBM", "NOW", "INTU", "PANW",
    "ANET", "SNPS", "CDNS", "FTNT", "WDAY",
]

COMMUNICATION = [
    "GOOGL", "GOOG", "META", "NFLX", "DIS",
    "TMUS", "VZ", "T", "CMCSA", "CHTR",
    "EA", "TTWO", "ROKU", "MTCH", "WBD",
]

CONSUMER_DISCRETIONARY = [
    "AMZN", "TSLA", "HD", "MCD", "NKE",
    "LOW", "SBUX", "BKNG", "TJX", "MAR",
    "GM", "F", "ROST", "AZO", "ORLY",
    "YUM", "CMG", "HLT", "EBAY", "ETSY",
]

FINANCIALS = [
    "BRK-B", "JPM", "V", "MA", "BAC",
    "WFC", "GS", "MS", "C", "AXP",
    "SCHW", "SPGI", "BLK", "PNC", "ICE",
]

HEALTHCARE = [
    "LLY", "JNJ", "UNH", "ABBV", "PFE",
    "MRK", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "ISRG", "VRTX", "REGN", "GILD",
]

INDUSTRIALS = [
    "CAT", "RTX", "HON", "UPS", "BA",
    "LMT", "GE", "DE", "ETN", "ADP",
    "UNP", "WM", "EMR", "PH", "NOC",
]

ENERGY = [
    "XOM", "CVX", "COP", "SLB", "EOG",
    "PSX", "MPC", "OXY", "KMI", "HAL",
    "DVN", "BKR", "FANG",
]

# =====================================================
# 🤖 AI / Software (개인 관심 섹터)
# =====================================================

AI_SOFTWARE = [
    "PLTR",
]

# =====================================================
# 📈 ETF (전략 자산)
# =====================================================

INDEX_ETF = ["SPY", "QQQ"]
DIVIDEND_ETF = ["SCHD", "JEPQ"]
LEVERAGE_ETF = ["SOXL", "NVDL", "SOLZ"]

# =====================================================
# 🪙 COMMODITY
# =====================================================

COMMODITY_GOLD = ["GLD", "GDXU", "UGL"]

# =====================================================
# ⚠️ 아래는 수정하지 말 것
# =====================================================

SECTOR_GROUPS = {

    # Semiconductor (세부분류 유지)
    "SEMICONDUCTOR_EQUIPMENT": SEMICONDUCTOR["EQUIPMENT"],
    "SEMICONDUCTOR_FABLESS": SEMICONDUCTOR["FABLESS"],
    "SEMICONDUCTOR_FOUNDRY": SEMICONDUCTOR["FOUNDRY"],
    "SEMICONDUCTOR_IDM": SEMICONDUCTOR["IDM"],

    # Core sectors
    "TECHNOLOGY": TECHNOLOGY,
    "COMMUNICATION": COMMUNICATION,
    "CONSUMER_DISCRETIONARY": CONSUMER_DISCRETIONARY,
    "FINANCIALS": FINANCIALS,
    "HEALTHCARE": HEALTHCARE,
    "INDUSTRIALS": INDUSTRIALS,
    "ENERGY": ENERGY,

    # Custom focus
    "AI_SOFTWARE": AI_SOFTWARE,

    # ETFs / Commodities
    "INDEX_ETF": INDEX_ETF,
    "DIVIDEND_ETF": DIVIDEND_ETF,
    "LEVERAGE_ETF": LEVERAGE_ETF,
    "COMMODITY_GOLD": COMMODITY_GOLD,
}

# =====================================================
# 📌 전체 즐겨찾기 자동 생성 (중복 제거)
# =====================================================

FAVORITES = sorted({
    symbol
    for group in SECTOR_GROUPS.values()
    for symbol in group
})

# =====================================================
# 🔧 Helper (선택)
# =====================================================

def get_symbols_by_sector(sector: str):
    return SECTOR_GROUPS.get(sector, [])


def get_all_semiconductors():
    symbols = set()
    for group in SEMICONDUCTOR.values():
        symbols.update(group)
    return sorted(symbols)
