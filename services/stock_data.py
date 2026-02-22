from pykrx import stock
from datetime import datetime, timedelta
import threading
import time


_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 300


def _get_cached(key: str):
    with _cache_lock:
        if key in _cache:
            value, timestamp = _cache[key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return value
            del _cache[key]
    return None


def _set_cached(key: str, value):
    with _cache_lock:
        _cache[key] = (value, time.time())


def _get_latest_trading_date() -> str:
    cached = _get_cached("latest_trading_date")
    if cached:
        return cached

    today = datetime.now()
    week_ago = (today - timedelta(days=10)).strftime("%Y%m%d")
    today_str = today.strftime("%Y%m%d")

    try:
        df = stock.get_market_ohlcv(week_ago, today_str, "005930")
        if not df.empty:
            last_date = str(df.index[-1])[:10].replace("-", "")
            _set_cached("latest_trading_date", last_date)
            return last_date
    except Exception:
        pass

    return today.strftime("%Y%m%d")


def get_stock_price(stock_code: str) -> dict:
    cache_key = f"price_{stock_code}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        date_str = _get_latest_trading_date()
        df = stock.get_market_ohlcv(date_str, date_str, stock_code)

        if df.empty:
            return _empty_price()

        row = df.iloc[-1]
        result = {
            "current_price": int(row.get("종가", 0)),
            "change_rate": round(float(row.get("등락률", 0)), 2),
            "open": int(row.get("시가", 0)),
            "high": int(row.get("고가", 0)),
            "low": int(row.get("저가", 0)),
            "volume": int(row.get("거래량", 0)),
            "date": _format_date(date_str),
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"[stock_data] price error ({stock_code}): {e}")
        return _empty_price()


def _empty_price() -> dict:
    return {
        "current_price": 0,
        "change_rate": 0.0,
        "open": 0,
        "high": 0,
        "low": 0,
        "volume": 0,
        "date": "",
    }


def get_stock_fundamental(stock_code: str) -> dict:
    cache_key = f"fundamental_{stock_code}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        date_str = _get_latest_trading_date()
        df = stock.get_market_fundamental(date_str, date_str, stock_code)

        if df.empty:
            return _empty_fundamental()

        row = df.iloc[-1]
        result = {
            "per": round(float(row.get("PER", 0)), 2),
            "pbr": round(float(row.get("PBR", 0)), 2),
            "eps": int(row.get("EPS", 0)),
            "bps": int(row.get("BPS", 0)),
            "div_yield": round(float(row.get("DIV", 0)), 2),
            "dps": int(row.get("DPS", 0)),
            "date": _format_date(date_str),
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"[stock_data] fundamental error ({stock_code}): {e}")
        return _empty_fundamental()


def _empty_fundamental() -> dict:
    return {
        "per": 0.0,
        "pbr": 0.0,
        "eps": 0,
        "bps": 0,
        "div_yield": 0.0,
        "dps": 0,
        "date": "",
    }


def get_stock_market_cap(stock_code: str) -> dict:
    cache_key = f"marketcap_{stock_code}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        date_str = _get_latest_trading_date()
        df = stock.get_market_cap(date_str, date_str, stock_code)

        if df.empty:
            return _empty_market_cap()

        row = df.iloc[-1]
        market_cap = int(row.get("시가총액", 0))
        result = {
            "market_cap": market_cap,
            "market_cap_text": _format_market_cap(market_cap),
            "shares": int(row.get("상장주식수", 0)),
            "date": _format_date(date_str),
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"[stock_data] market_cap error ({stock_code}): {e}")
        return _empty_market_cap()


def _empty_market_cap() -> dict:
    return {
        "market_cap": 0,
        "market_cap_text": "-",
        "shares": 0,
        "date": "",
    }


# ──────────────────────────────────────────────
# 히스토리 데이터 (차트 + 기술지표용)
# ──────────────────────────────────────────────


def get_stock_history(stock_code: str, months: int = 36) -> list[dict]:
    """3년(기본) OHLCV 히스토리. TradingView 차트 + 기술지표 계산용."""
    cache_key = f"history_{stock_code}_{months}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        end_date = _get_latest_trading_date()
        start_date = (
            datetime.strptime(end_date, "%Y%m%d") - timedelta(days=months * 30)
        ).strftime("%Y%m%d")

        df = stock.get_market_ohlcv(start_date, end_date, stock_code)
        if df.empty:
            return []

        result = []
        for idx, row in df.iterrows():
            date_str = str(idx)[:10]
            result.append(
                {
                    "date": date_str,
                    "open": int(row.get("시가", 0)),
                    "high": int(row.get("고가", 0)),
                    "low": int(row.get("저가", 0)),
                    "close": int(row.get("종가", 0)),
                    "volume": int(row.get("거래량", 0)),
                }
            )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"[stock_data] history error ({stock_code}): {e}")
        return []


def get_kospi_history(months: int = 3) -> list[dict]:
    """KOSPI 지수 히스토리 (시장 비교용)."""
    cache_key = f"kospi_history_{months}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        end_date = _get_latest_trading_date()
        start_date = (
            datetime.strptime(end_date, "%Y%m%d") - timedelta(days=months * 30)
        ).strftime("%Y%m%d")

        df = stock.get_index_ohlcv(start_date, end_date, "1001")
        if df.empty:
            return []

        result = []
        for idx, row in df.iterrows():
            date_str = str(idx)[:10]
            result.append(
                {
                    "date": date_str,
                    "close": round(float(row.get("종가", 0)), 2),
                    "volume": int(row.get("거래량", 0)),
                }
            )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"[stock_data] kospi error: {e}")
        return []


def calc_indicators(history: list[dict]) -> dict:
    """OHLCV 히스토리로부터 기술지표 계산."""
    if not history or len(history) < 5:
        return _empty_indicators()

    closes = [d["close"] for d in history]
    volumes = [d["volume"] for d in history]

    sma5 = _sma(closes, 5)
    sma20 = _sma(closes, 20)
    sma60 = _sma(closes, 60)
    rsi14 = _rsi(closes, 14)
    volume_ratio = _volume_ratio(volumes, 20)
    high_52w = max(d["high"] for d in history[-min(252, len(history)) :])
    low_52w = min(d["low"] for d in history[-min(252, len(history)) :])

    return {
        "sma5": sma5,
        "sma20": sma20,
        "sma60": sma60,
        "rsi14": rsi14,
        "volume_ratio": volume_ratio,
        "high_52w": high_52w,
        "low_52w": low_52w,
    }


def _empty_indicators() -> dict:
    return {
        "sma5": 0,
        "sma20": 0,
        "sma60": 0,
        "rsi14": 50,
        "volume_ratio": 1.0,
        "high_52w": 0,
        "low_52w": 0,
    }


def _sma(values: list, period: int) -> int:
    if len(values) < period:
        return int(sum(values) / len(values)) if values else 0
    return int(sum(values[-period:]) / period)


def _rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _volume_ratio(volumes: list, period: int = 20) -> float:
    if len(volumes) < 2:
        return 1.0

    today_vol = volumes[-1]
    avg_vol = sum(volumes[-period - 1 : -1]) / min(period, len(volumes) - 1)

    if avg_vol == 0:
        return 1.0

    return round(today_vol / avg_vol, 2)


# ──────────────────────────────────────────────
# 통합 데이터 함수
# ──────────────────────────────────────────────


def get_stock_all_data(stock_code: str) -> dict:
    """즉시 데이터: 가격 + 펀더멘탈 + 시총."""
    price = get_stock_price(stock_code)
    fundamental = get_stock_fundamental(stock_code)
    market_cap = get_stock_market_cap(stock_code)

    return {
        "price": price,
        "fundamental": fundamental,
        "market_cap": market_cap,
    }


def get_stock_full_data(stock_code: str) -> dict:
    """전체 데이터: 즉시 + 히스토리 + 기술지표. /api/stock 응답용."""
    basic = get_stock_all_data(stock_code)
    history = get_stock_history(stock_code, months=36)
    indicators = calc_indicators(history)

    return {
        **basic,
        "chart_data": history,
        "indicators": indicators,
    }


# ──────────────────────────────────────────────
# 랜딩 종목 랭킹 (4개 카테고리)
# ──────────────────────────────────────────────


def _get_all_ohlcv():
    """전 종목 OHLCV 캐시. 4개 카테고리 공유."""
    cached = _get_cached("all_ohlcv")
    if cached is not None:
        return cached

    date_str = _get_latest_trading_date()
    df = stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
    if df is not None and not df.empty:
        _set_cached("all_ohlcv", df)
    return df


def _build_stock_list(tickers, df_ohlcv, limit: int) -> list[dict]:
    """티커 목록으로 종목 정보 리스트 생성."""
    result = []
    max_volume = 0

    for ticker in tickers:
        if len(result) >= limit:
            break

        row = df_ohlcv.loc[ticker]
        close_price = int(row.get("종가", 0))
        volume = int(row.get("거래량", 0))
        change_rate = round(float(row.get("등락률", 0)), 2)

        if close_price <= 0:
            continue

        try:
            name = stock.get_market_ticker_name(ticker)
        except Exception:
            name = ticker

        if max_volume == 0 and volume > 0:
            max_volume = volume

        result.append({
            "rank": len(result) + 1,
            "name": name,
            "code": ticker,
            "current_price": close_price,
            "change_rate": change_rate,
            "volume": volume,
            "volume_ratio": round(volume / max_volume * 100) if max_volume else 0,
        })

    return result


def get_popular_stocks(limit: int = 10, category: str = "volume_top") -> list[dict]:
    """카테고리별 종목 랭킹 반환."""
    cache_key = f"popular_{category}_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        df_ohlcv = _get_all_ohlcv()
        if df_ohlcv is None or df_ohlcv.empty:
            return []

        # 종가 > 0인 종목만
        df = df_ohlcv[df_ohlcv["종가"] > 0].copy()

        if category == "volume_top":
            # 거래량 상위 (거래량 > 0)
            df = df[df["거래량"] > 0]
            df = df.sort_values("거래량", ascending=False)
            tickers = df.head(limit * 3).index.tolist()

        elif category == "volume_zero":
            # 거래량 없는 종목 (거래량 == 0)
            df = df[df["거래량"] == 0]
            # 종가 기준 내림차순 (시가총액 큰 것부터)
            df = df.sort_values("종가", ascending=False)
            tickers = df.head(limit * 3).index.tolist()

        elif category == "top_gainers":
            # 급상승 (등락률 상위, 거래량 > 0)
            df = df[df["거래량"] > 0]
            df = df.sort_values("등락률", ascending=False)
            tickers = df.head(limit * 3).index.tolist()

        elif category == "top_losers":
            # 급하강 (등락률 하위, 거래량 > 0)
            df = df[df["거래량"] > 0]
            df = df.sort_values("등락률", ascending=True)
            tickers = df.head(limit * 3).index.tolist()

        else:
            return []

        result = _build_stock_list(tickers, df_ohlcv, limit)
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"[stock_data] popular stocks error ({category}): {e}")
        return []


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────


def _format_date(date_str: str) -> str:
    if len(date_str) == 8:
        return f"{date_str[:4]}년 {date_str[4:6]}월 {date_str[6:]}일"
    return date_str


def _format_market_cap(value: int) -> str:
    if value <= 0:
        return "-"

    jo = value // 1_000_000_000_000
    eok = (value % 1_000_000_000_000) // 100_000_000

    parts = []
    if jo > 0:
        parts.append(f"{jo:,}조")
    if eok > 0:
        parts.append(f"{eok:,}억")

    return " ".join(parts) if parts else "1억 미만"
