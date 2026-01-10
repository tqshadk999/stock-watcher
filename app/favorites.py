# =========================
# 산업군별 즐겨찾기 종목
# =========================

SEMICONDUCTOR = [
    "NVDA", "AMD", "INTC", "MU", "AVGO", "QCOM"
]

AI_SOFTWARE = [
    "PLTR"
]

HEALTHCARE = [
    "LLY", "UNH"
]

FINANCIAL = [
    "BRK-B"
]

INDEX_ETF = [
    "SPY", "QQQ"
]

DIVIDEND_ETF = [
    "SCHD", "JEPQ"
]

LEVERAGE_ETF = [
    "SOXL", "NVDL", "SOLZ"
]

COMMODITY_GOLD = [
    "GLD", "GDXU", "UGL"
]

# =========================
# ⚠️ 아래는 수정하지 말 것
# =========================

SECTOR_GROUPS = {
    "SEMICONDUCTOR": SEMICONDUCTOR,
    "AI_SOFTWARE": AI_SOFTWARE,
    "HEALTHCARE": HEALTHCARE,
    "FINANCIAL": FINANCIAL,
    "INDEX_ETF": INDEX_ETF,
    "DIVIDEND_ETF": DIVIDEND_ETF,
    "LEVERAGE_ETF": LEVERAGE_ETF,
    "COMMODITY_GOLD": COMMODITY_GOLD,
}

# 전체 즐겨찾기 자동 생성 (중복 제거)
FAVORITES = sorted({symbol for group in SECTOR_GROUPS.values() for symbol in group})
