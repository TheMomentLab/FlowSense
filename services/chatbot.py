"""
FlowSense 챗봇 서비스.
사용자 질문을 받아 주식 데이터를 조회하고 AI가 자연어로 답변한다.
SSE 스트리밍으로 응답.
"""

import json

from services.llm_provider import PROVIDERS, get_client
from services.stock_search import search_stocks, get_stock_code
from services.stock_data import (
    get_stock_price,
    get_stock_fundamental,
    get_stock_market_cap,
    get_popular_stocks,
)
from services.news_crawler import get_news
from services.news_cache import get_cached_news


SYSTEM_PROMPT = """당신은 FlowSense의 AI 주식 분석 어시스턴트입니다.
한국 주식 시장(KOSPI/KOSDAQ)에 대한 질문에 답합니다.
이모지를 절대 사용하지 마세요. 간결하고 명확하게 답하세요.

[역할]
- 주식 용어(PER, PBR, RSI 등)를 쉽게 설명
- 특정 종목 데이터를 바탕으로 현황 분석
- 인기 종목, 거래량 상위 종목 정보 제공
- 투자 판단은 직접 내리지 않되, 데이터 기반 인사이트 제공

[규칙]
- 데이터가 제공되면 반드시 활용하여 구체적으로 답변
- 숫자는 읽기 쉽게 포맷 (예: 89,400원, 3.5배)
- 투자 권유가 아닌 정보 제공임을 기억
- 한국어로 답변
- 마크다운 형식 사용 가능 (볼드, 리스트 등)
"""


# ──────────────────────────────────────────────
# 컨텍스트 수집
# ──────────────────────────────────────────────


def _extract_stock_names(message: str) -> list[str]:
    """사용자 메시지에서 종목명 후보를 추출."""
    results = search_stocks(message, limit=3)
    found = []
    for r in results:
        if r["name"] in message:
            found.append(r["name"])
    return found


def _detect_intent(message: str) -> str:
    """간단한 의도 분류."""
    msg = message.lower()

    # 인기 / 상위 / 랭킹 관련
    ranking_keywords = [
        "인기",
        "상위",
        "높은",
        "많은",
        "거래량",
        "랭킹",
        "순위",
        "탑",
        "top",
    ]
    if any(k in msg for k in ranking_keywords):
        return "ranking"

    # 용어 설명
    terms = [
        "per",
        "pbr",
        "eps",
        "bps",
        "rsi",
        "sma",
        "이동평균",
        "배당",
        "시가총액",
        "볼린저",
        "macd",
    ]
    what_keywords = ["뭐", "무엇", "무슨", "설명", "알려", "의미", "뜻"]
    if any(t in msg for t in terms) and any(w in msg for w in what_keywords):
        return "explain_term"

    # 특정 종목 질문
    stock_names = _extract_stock_names(message)
    if stock_names:
        return "stock_query"

    return "general"


def _build_context(message: str, current_stock: str | None = None) -> str:
    """질문 의도에 따라 데이터 컨텍스트를 수집."""
    intent = _detect_intent(message)
    context_parts = []

    if intent == "ranking":
        popular = get_popular_stocks(10)
        if popular:
            lines = ["[거래량 상위 인기 종목]"]
            for s in popular:
                sign = "+" if s["change_rate"] >= 0 else ""
                lines.append(
                    f"{s['rank']}. {s['name']} ({s['code']}) "
                    f"- 현재가: {s['current_price']:,}원 "
                    f"({sign}{s['change_rate']}%) "
                    f"거래량: {s['volume']:,}"
                )
            context_parts.append("\n".join(lines))

    elif intent == "stock_query" or current_stock:
        # 메시지에서 종목명 추출, 또는 현재 보고 있는 종목 사용
        stock_names = _extract_stock_names(message)
        target_name = stock_names[0] if stock_names else current_stock

        if target_name:
            stock_info = get_stock_code(target_name)
            if stock_info:
                code = stock_info["code"]
                price = get_stock_price(code)
                fund = get_stock_fundamental(code)
                mcap = get_stock_market_cap(code)

                parts = [f"[{target_name} ({code}) 데이터]"]

                if price.get("current_price"):
                    sign = "+" if price["change_rate"] >= 0 else ""
                    parts.append(
                        f"현재가: {price['current_price']:,}원 "
                        f"({sign}{price['change_rate']}%) "
                        f"거래량: {price['volume']:,}"
                    )

                if mcap.get("market_cap_text") and mcap["market_cap_text"] != "-":
                    parts.append(f"시가총액: {mcap['market_cap_text']}")

                if fund.get("per"):
                    parts.append(
                        f"PER: {fund['per']}배 | PBR: {fund['pbr']}배 | "
                        f"EPS: {fund['eps']:,}원 | BPS: {fund['bps']:,}원 | "
                        f"배당률: {fund['div_yield']}%"
                    )

                news = get_cached_news(code)
                if news is None:
                    news = get_news(code, target_name, limit=5)
                if news:
                    parts.append("[최근 뉴스]")
                    for n in news[:5]:
                        parts.append(f"  - {n['title']} ({n.get('date', '')})")

                context_parts.append("\n".join(parts))

    # 현재 종목 컨텍스트 (분석 페이지에서 질문할 때)
    if current_stock and intent != "stock_query":
        stock_info = get_stock_code(current_stock)
        if stock_info:
            code = stock_info["code"]
            price = get_stock_price(code)
            if price.get("current_price"):
                context_parts.append(
                    f"[현재 분석 중인 종목: {current_stock}] "
                    f"현재가: {price['current_price']:,}원"
                )

    return "\n\n".join(context_parts)


# ──────────────────────────────────────────────
# 스트리밍 응답
# ──────────────────────────────────────────────


def chat_stream(message: str, current_stock: str | None = None):
    """
    SSE 스트리밍 제너레이터.
    yield 형식: "data: {json}\n\n"
    """
    if not PROVIDERS:
        yield 'data: {"error": "API 키가 설정되지 않았습니다."}\n\n'
        return

    # 컨텍스트 수집
    context = _build_context(message, current_stock)

    user_content = message
    if context:
        user_content = f"{context}\n\n---\n사용자 질문: {message}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    for provider in PROVIDERS:
        try:
            client = get_client(provider)

            response = client.chat.completions.create(
                model=provider["chat_model"],
                messages=messages,
                max_tokens=1200,
                temperature=0.5,
                stream=True,
            )

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    payload = json.dumps({"text": delta.content}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

            yield 'data: {"done": true}\n\n'
            return  # 성공 시 다음 프로바이더 시도하지 않음

        except Exception as e:
            print(f"[chatbot] streaming error: {e}")
            continue

    yield 'data: {"error": "모든 AI 서비스가 응답하지 않습니다."}\n\n'
