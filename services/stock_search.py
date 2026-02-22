import json
import os
import time
import threading

_stock_list = None
_stock_list_lock = threading.Lock()
_last_refresh = 0
REFRESH_INTERVAL = 86400


def _load_stocks():
    global _stock_list, _last_refresh

    with _stock_list_lock:
        now = time.time()
        if _stock_list is not None and (now - _last_refresh) < REFRESH_INTERVAL:
            return _stock_list

        pykrx_stocks = _load_from_pykrx()
        if pykrx_stocks:
            _stock_list = pykrx_stocks
            _last_refresh = now
            return _stock_list

        if _stock_list is not None:
            return _stock_list

        _stock_list = _load_from_json()
        _last_refresh = now
        return _stock_list


def _load_from_pykrx() -> list:
    try:
        from pykrx import stock as pykrx_api

        result = []
        for market in ["KOSPI", "KOSDAQ"]:
            tickers = pykrx_api.get_market_ticker_list(market=market)
            for ticker in tickers:
                name = pykrx_api.get_market_ticker_name(ticker)
                if name:
                    result.append({"name": name, "code": ticker, "market": market})

        if len(result) > 100:
            _save_to_json(result)
            return result

    except Exception as e:
        print(f"[stock_search] pykrx load failed: {e}")

    return []


def _save_to_json(stocks: list) -> None:
    try:
        data_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "stock_list.json"
        )
        import tempfile

        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(data_path), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"stocks": stocks}, f, ensure_ascii=False)
            os.replace(tmp_path, data_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        print(f"[stock_search] JSON save failed: {e}")


def _load_from_json() -> list:
    try:
        data_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "stock_list.json"
        )
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["stocks"]
    except Exception as e:
        print(f"[stock_search] JSON load failed: {e}")
        return []


def search_stocks(query: str, limit: int = 10) -> list:
    stocks = _load_stocks()
    query_lower = query.lower()

    results = []
    for s in stocks:
        name_lower = s["name"].lower()
        if query_lower in name_lower:
            results.append(
                {"name": s["name"], "code": s["code"], "market": s["market"]}
            )

    results.sort(
        key=lambda x: (not x["name"].lower().startswith(query_lower), x["name"])
    )
    return results[:limit]


def get_stock_code(stock_name: str) -> dict | None:
    stocks = _load_stocks()

    for s in stocks:
        if s["name"] == stock_name:
            return {"name": s["name"], "code": s["code"], "market": s["market"]}

    return None
