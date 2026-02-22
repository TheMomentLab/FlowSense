import os
import threading
import atexit
import time
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request, Response
from apscheduler.schedulers.background import BackgroundScheduler
from pykrx import stock as pykrx_api

from services.stock_search import search_stocks, get_stock_code
from services.news_crawler import get_news, get_disclosures
from services.stock_data import get_stock_full_data, get_popular_stocks
from services.ai_analyzer import judge_stock
from services.news_cache import get_cached_news, update_all_news, get_cache_status
from services.chatbot import chat_stream
from services.llm_provider import PROVIDERS, get_client

app = Flask(__name__)

SUMMARY_CACHE_TTL = 3600
summary_cache: dict[str, tuple[float, str]] = {}
SECTOR_CACHE_TTL = 600
sector_cache: tuple[float, list[dict[str, float | str]]] | None = None
DIGEST_CACHE_TTL = 21600
digest_cache: tuple[float, dict[str, str | list[dict[str, float | str]]]] | None = None

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=update_all_news, trigger="cron", hour=6, minute=0, id="daily_news_update"
)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/analyze")
def analyze():
    return render_template("analyze.html")


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if len(query) < 1:
        return jsonify([])

    results = search_stocks(query)
    return jsonify(results)


@app.route("/api/stock")
def api_stock():
    stock_name = request.args.get("name", "").strip()

    if not stock_name:
        return jsonify({"error": "종목명을 입력해주세요"}), 400

    stock_info = get_stock_code(stock_name)
    if not stock_info:
        return jsonify({"error": "종목을 찾을 수 없습니다"}), 404

    stock_code = stock_info["code"]

    news_list = get_cached_news(stock_code)
    if news_list is None:
        news_list = get_news(stock_code, stock_name)

    disclosure_list = get_disclosures(stock_code)
    stock_data = get_stock_full_data(stock_code)

    return jsonify(
        {
            "stock_name": stock_name,
            "stock_code": stock_code,
            "market": stock_info.get("market", ""),
            **stock_data,
            "news": news_list[:8],
            "disclosures": disclosure_list[:5],
        }
    )


@app.route("/api/stock/summary")
def api_stock_summary():
    stock_code = request.args.get("code", "").strip()

    if not stock_code:
        return jsonify({"error": "종목 코드를 입력해주세요"}), 400

    now = time.time()
    cached = summary_cache.get(stock_code)
    if cached and now - cached[0] < SUMMARY_CACHE_TTL:
        return jsonify({"summary": cached[1]})
    if cached:
        summary_cache.pop(stock_code, None)

    try:
        stock_data = get_stock_full_data(stock_code)
    except Exception:
        return jsonify({"summary": ""})

    fundamental = stock_data.get("fundamental", {})
    price = stock_data.get("price", {})
    user_prompt = (
        f"PER: {fundamental.get('per', '-')}, "
        f"PBR: {fundamental.get('pbr', '-')}, "
        f"change_rate: {price.get('change_rate', '-')}."
    )

    summary = ""
    for provider in PROVIDERS:
        try:
            client = get_client(provider)
            response = client.chat.completions.create(
                model=provider["chat_model"],
                messages=[
                    {
                        "role": "system",
                        "content": "주식 데이터를 보고 초보자를 위한 한 줄 요약을 해주세요. 30자 이내로 간결하게. 이모지 사용 금지.",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=60,
                temperature=0.3,
            )
            content = response.choices[0].message.content if response.choices else ""
            if not content:
                continue
            summary = content.strip().split("\n", 1)[0][:30]
            if summary:
                summary_cache[stock_code] = (now, summary)
                break
        except Exception:
            continue

    return jsonify({"summary": summary})



def _load_sector_changes() -> list[dict[str, float | str]]:
    today = datetime.now()

    for end_offset in range(0, 8):
        end_dt = today - timedelta(days=end_offset)
        end_date = end_dt.strftime("%Y%m%d")

        for span in range(1, 8):
            start_date = (end_dt - timedelta(days=span)).strftime("%Y%m%d")
            try:
                df = pykrx_api.get_index_price_change_by_ticker(
                    start_date, end_date, market="KOSPI"
                )
            except Exception:
                continue

            if df is None or df.empty:
                continue

            sectors: list[dict[str, float | str]] = []
            for ticker, row in df.iterrows():
                change_rate = row.get("등락률", 0) or 0
                ticker_str = str(ticker)
                try:
                    change_rate = round(float(change_rate), 2)
                except (TypeError, ValueError):
                    change_rate = 0.0

                sectors.append(
                    {
                        "name": ticker_str,
                        "change_rate": change_rate,
                        "ticker": ticker_str,
                    }
                )

            sectors.sort(key=lambda item: abs(float(item["change_rate"])), reverse=True)
            return sectors

    return []


def _load_weekly_sector_changes() -> list[dict[str, float | str]]:
    today = datetime.now()

    for end_offset in range(0, 8):
        end_dt = today - timedelta(days=end_offset)
        end_date = end_dt.strftime("%Y%m%d")
        start_date = (end_dt - timedelta(days=7)).strftime("%Y%m%d")

        try:
            df = pykrx_api.get_index_price_change_by_ticker(
                start_date, end_date, market="KOSPI"
            )
        except Exception:
            continue

        if df is None or df.empty:
            continue

        sectors: list[dict[str, float | str]] = []
        for ticker, row in df.iterrows():
            change_rate = row.get("등락률", 0) or 0
            ticker_str = str(ticker)
            try:
                change_rate = round(float(change_rate), 2)
            except (TypeError, ValueError):
                change_rate = 0.0

            sectors.append(
                {
                    "name": ticker_str,
                    "change_rate": change_rate,
                    "ticker": ticker_str,
                }
            )

        return sectors

    return []


def _build_market_digest(
    top_sectors: list[dict[str, float | str]],
    bottom_sectors: list[dict[str, float | str]],
    avg_change: float,
) -> str:
    top_text = ", ".join(
        [f"{item['name']}({item['change_rate']}%)" for item in top_sectors]
    )
    bottom_text = ", ".join(
        [f"{item['name']}({item['change_rate']}%)" for item in bottom_sectors]
    )

    if avg_change > 0.2:
        trend = "완만한 상승"
    elif avg_change < -0.2:
        trend = "완만한 하락"
    else:
        trend = "보합"

    user_prompt = (
        f"상승 상위 업종: {top_text}. "
        f"하락 상위 업종: {bottom_text}. "
        f"주간 평균 등락률: {avg_change:.2f}% ({trend})."
    )

    for provider in PROVIDERS:
        try:
            client = get_client(provider)
            response = client.chat.completions.create(
                model=provider["chat_model"],
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식시장 주간 요약을 작성하는 전문가입니다. 초보 투자자도 이해할 수 있게 간결하게 작성하세요. 이모지 사용 금지. 200자 이내.",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=180,
                temperature=0.3,
            )
            content = response.choices[0].message.content if response.choices else ""
            if not content:
                continue
            digest = content.strip().replace("\n", " ")
            if digest:
                return digest[:200]
        except Exception:
            continue

    return (
        f"이번 주 시장은 {trend} 흐름입니다. 상승 업종은 {top_text}, 하락 업종은 {bottom_text} 중심으로 변동이 컸습니다."
    )[:200]


@app.route("/api/sectors")
def api_sectors():
    global sector_cache

    now = time.time()
    if sector_cache and now - sector_cache[0] < SECTOR_CACHE_TTL:
        return jsonify({"sectors": sector_cache[1]})

    sectors = _load_sector_changes()
    sector_cache = (now, sectors)
    return jsonify({"sectors": sectors})


@app.route("/api/digest")
def api_digest():
    global digest_cache

    no_cache = request.args.get("no_cache", "").strip() == "1"
    now = time.time()
    if not no_cache and digest_cache and now - digest_cache[0] < DIGEST_CACHE_TTL:
        return jsonify(digest_cache[1])

    sectors = _load_weekly_sector_changes()
    if not sectors:
        return jsonify({"error": "시장 요약 데이터를 불러오지 못했습니다"}), 503

    sorted_sectors = sorted(
        sectors,
        key=lambda item: float(item.get("change_rate", 0) or 0),
        reverse=True,
    )
    top_sectors = sorted_sectors[:3]
    bottom_sectors = list(reversed(sorted_sectors[-3:]))
    avg_change = sum(float(item.get("change_rate", 0) or 0) for item in sectors) / max(
        len(sectors), 1
    )

    digest = _build_market_digest(top_sectors, bottom_sectors, avg_change)
    generated_at = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    payload = {
        "digest": digest,
        "generated_at": generated_at,
        "top_sectors": top_sectors,
        "bottom_sectors": bottom_sectors,
    }
    digest_cache = (now, payload)
    return jsonify(payload)


@app.route("/api/judge")
def api_judge():
    agent_id = request.args.get("agent", "").strip()
    stock_name = request.args.get("name", "").strip()

    if not agent_id or not stock_name:
        return jsonify({"error": "agent, name 파라미터 필요"}), 400

    stock_info = get_stock_code(stock_name)
    if not stock_info:
        return jsonify({"error": "종목을 찾을 수 없습니다"}), 404

    stock_code = stock_info["code"]
    stock_data = get_stock_full_data(stock_code)

    news_list = get_cached_news(stock_code)
    if news_list is None:
        news_list = get_news(stock_code, stock_name)

    disclosure_list = get_disclosures(stock_code)

    result = judge_stock(agent_id, stock_name, stock_data, news_list, disclosure_list)
    return jsonify(result)


@app.route("/api/popular")
def api_popular():
    limit = request.args.get("limit", "10")
    category = request.args.get("category", "volume_top")
    try:
        limit = min(int(limit), 20)
    except ValueError:
        limit = 10
    valid = {"volume_top", "volume_zero", "top_gainers", "top_losers"}
    if category not in valid:
        category = "volume_top"
    return jsonify(get_popular_stocks(limit, category))


@app.route("/api/whatif")
def api_whatif():
    stock_name = request.args.get("name", "").strip()
    amount_raw = request.args.get("amount", "").strip()
    date_raw = request.args.get("date", "").strip()

    if not stock_name:
        return jsonify({"error": "종목명을 입력해주세요"}), 400

    try:
        amount = int(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "투자 금액은 0보다 큰 정수여야 합니다"}), 400

    try:
        invest_dt = datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "날짜 형식은 YYYY-MM-DD 이어야 합니다"}), 400

    if invest_dt > datetime.now():
        return jsonify({"error": "미래 날짜는 입력할 수 없습니다"}), 400

    stock_info = get_stock_code(stock_name)
    if not stock_info:
        return jsonify({"error": "종목을 찾을 수 없습니다"}), 404

    stock_code = stock_info["code"]
    start_date = invest_dt.strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")

    try:
        df = pykrx_api.get_market_ohlcv_by_date(start_date, end_date, stock_code)
    except Exception:
        return jsonify({"error": "주가 데이터를 불러오지 못했습니다"}), 500

    if df is None or df.empty:
        return jsonify({"error": "입력한 날짜 이후 주가 데이터가 없습니다"}), 404

    buy_row = df.iloc[0]
    current_row = df.iloc[-1]

    buy_price = int(buy_row.get("종가", 0))
    current_price = int(current_row.get("종가", 0))
    if buy_price <= 0 or current_price <= 0:
        return jsonify({"error": "유효한 종가 데이터를 찾을 수 없습니다"}), 404

    shares = amount / buy_price
    current_value = int(round(shares * current_price))
    profit = current_value - amount
    profit_rate = round((profit / amount) * 100, 2)
    invest_date = str(df.index[0])[:10]

    return jsonify(
        {
            "stock_name": stock_info["name"],
            "invest_date": invest_date,
            "invest_amount": amount,
            "buy_price": buy_price,
            "current_price": current_price,
            "current_value": current_value,
            "profit": profit,
            "profit_rate": profit_rate,
        }
    )


@app.route("/api/chat")
def api_chat():
    message = request.args.get("message", "").strip()
    current_stock = request.args.get("stock", "").strip() or None

    if not message:
        return jsonify({"error": "메시지를 입력해주세요"}), 400

    return Response(
        chat_stream(message, current_stock),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/cache/status")
def api_cache_status():
    return jsonify(get_cache_status())


@app.route("/api/cache/update", methods=["POST"])
def api_cache_update():
    threading.Thread(target=update_all_news, daemon=True).start()
    return jsonify(
        {
            "message": "캐시 업데이트가 백그라운드에서 시작되었습니다",
            "status": get_cache_status(),
        }
    )


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "요청하신 API를 찾을 수 없습니다"}), 404
    return render_template("landing.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "서버 내부 오류가 발생했습니다"}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("FlowSense - Stock AI Analyzer")
    print("=" * 50)
    is_dev = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=is_dev, port=5000, use_reloader=False)
