import yfinance as yf

# ✅ 필요하면 여기에 "대체 티커"를 추가해라
# 예: "BRK.B" -> "BRK-B" 는 universe에서 normalize 하므로 굳이 안 넣어도 됨
REPLACEMENTS = {
    # 예시:
    # "GOOG.L": "GOOGL",
}

_valid_cache = {}
_invalid_cache = {}

def resolve_symbol(symbol: str) -> str:
    """대체 티커가 있으면 치환, 없으면 원본."""
    return REPLACEMENTS.get(symbol, symbol)

def is_yfinance_valid(symbol: str) -> bool:
    """
    yfinance에서 유효하게 데이터 조회 가능한 티커인지 빠르게 검사.
    - fast_info 우선(가벼움)
    - 실패 시 info로 한 번 더 시도(다소 무거움)
    """
    if symbol in _valid_cache:
        return True
    if symbol in _invalid_cache:
        return False

    try:
        t = yf.Ticker(symbol)

        # fast_info가 있으면 우선 사용
        try:
            fi = t.fast_info
            # last_price 또는 market_cap 같은 키가 잡히면 "유효"로 간주
            if fi and (fi.get("last_price") is not None or fi.get("market_cap") is not None):
                _valid_cache[symbol] = True
                return True
        except Exception:
            pass

        # fast_info 실패 시 info로 fallback (여기서도 최소 key 확인)
        info = t.info
        if info and (info.get("regularMarketPrice") is not None or info.get("shortName") is not None):
            _valid_cache[symbol] = True
            return True

    except Exception:
        pass

    _invalid_cache[symbol] = True
    return False

def sanitize_symbols(symbols):
    """
    symbols 목록에서:
    - 대체 티커 적용
    - yfinance 불가 티커는 제거
    반환: (valid_symbols, dropped_originals)
    """
    valid = []
    dropped = []

    for s in symbols:
        rs = resolve_symbol(s)
        if is_yfinance_valid(rs):
            valid.append(rs)
        else:
            dropped.append(s)

    # 중복 제거 유지(입력 순서 유지)
    seen = set()
    valid_unique = []
    for v in valid:
        if v not in seen:
            valid_unique.append(v)
            seen.add(v)

    return valid_unique, dropped
