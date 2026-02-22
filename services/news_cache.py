import json
import os
import threading
from datetime import datetime
from services.news_crawler import get_news
from services.stock_search import _load_stocks

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "news_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "news_data.json")

_cache_lock = threading.Lock()
_memory_cache = None
_memory_cache_mtime = 0


def ensure_cache_dir():
    """캐시 디렉토리 생성"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _load_cache_from_disk() -> dict | None:
    """디스크에서 캐시 파일 로드 (인메모리 캐시 활용)"""
    global _memory_cache, _memory_cache_mtime

    if not os.path.exists(CACHE_FILE):
        return None

    try:
        file_mtime = os.path.getmtime(CACHE_FILE)
        if _memory_cache is not None and file_mtime == _memory_cache_mtime:
            return _memory_cache

        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        _memory_cache = data
        _memory_cache_mtime = file_mtime
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"캐시 읽기 오류: {e}")
        return None


def _save_cache_to_disk(cache_data: dict):
    """캐시 데이터를 디스크에 안전하게 저장 (atomic write)"""
    global _memory_cache, _memory_cache_mtime

    ensure_cache_dir()
    tmp_file = CACHE_FILE + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, CACHE_FILE)  # atomic on POSIX
        _memory_cache = cache_data
        _memory_cache_mtime = os.path.getmtime(CACHE_FILE)
    except OSError as e:
        print(f"캐시 저장 오류: {e}")
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


def update_all_news():
    """
    모든 종목의 뉴스를 크롤링하여 캐시에 저장
    하루에 한 번 실행됨
    """
    stocks = _load_stocks()

    cache_data = {
        "last_updated": datetime.now().isoformat(),
        "stocks": {},
    }

    print(f"[{datetime.now()}] 뉴스 캐시 업데이트 시작...")

    for stock in stocks:
        try:
            news_list = get_news(stock["code"], stock["name"], limit=10)
            cache_data["stocks"][stock["code"]] = {
                "name": stock["name"],
                "news": news_list,
                "updated_at": datetime.now().isoformat(),
            }
            print(f"  - {stock['name']}: {len(news_list)}건")
        except Exception as e:
            print(f"  - {stock['name']}: 오류 - {e}")
            cache_data["stocks"][stock["code"]] = {
                "name": stock["name"],
                "news": [],
                "updated_at": datetime.now().isoformat(),
                "error": str(e),
            }

    with _cache_lock:
        _save_cache_to_disk(cache_data)

    print(f"[{datetime.now()}] 뉴스 캐시 업데이트 완료!")
    return cache_data


def get_cached_news(stock_code: str) -> list | None:
    """
    캐시에서 뉴스 조회
    캐시가 없으면 None 반환 (실시간 크롤링 필요)
    """
    with _cache_lock:
        cache_data = _load_cache_from_disk()

    if cache_data is None:
        return None

    if stock_code in cache_data.get("stocks", {}):
        return cache_data["stocks"][stock_code].get("news", [])

    return None


def get_cache_status() -> dict:
    """캐시 상태 조회"""
    with _cache_lock:
        cache_data = _load_cache_from_disk()

    if cache_data is not None:
        return {
            "exists": True,
            "last_updated": cache_data.get("last_updated"),
            "stock_count": len(cache_data.get("stocks", {})),
        }

    return {"exists": False}
