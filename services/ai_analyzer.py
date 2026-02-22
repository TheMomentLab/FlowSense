from services.llm_provider import PROVIDERS, get_client
import json
import os


def _load_psychology_guide() -> str:
    guide_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "psychology_guide.json"
    )
    try:
        with open(guide_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lines = []
        for bias in data.get("biases", []):
            lines.append(
                f"- {bias['name']}: {bias['description']} "
                f"(함정: {bias['investor_trap']})"
            )
        return "\n".join(lines)
    except Exception:
        return ""


PSYCHOLOGY_CONTEXT = _load_psychology_guide()


AGENT_BUFFETT = {
    "id": "buffett",
    "name": "Warren Buffett",
    "requires": [
        "fundamental",
        "market_cap",
        "price",
        "news",
        "disclosures",
        "indicators",
    ],
    "system": f"""당신은 워런 버핏의 투자 프레임워크로 판단하는 분석 에이전트입니다.
이모지를 절대 사용하지 마세요. 간결하고 명확하게 답하세요.

[판단 프레임워크]
1. 이해 가능한 사업인가? - 사업 모델이 단순하고 예측 가능한지
2. 경제적 해자(Moat)가 있는가? - 시장 지배력, 브랜드, 전환 비용, 네트워크 효과
3. 합리적 가격인가? - PER 15배 이하 선호, PBR과 EPS 대비 현재가 평가
4. 장기 보유 적합한가? - 이익 안정성, 배당 이력, 경영진 신뢰도
5. 안전 마진이 있는가? - BPS 대비 현재가, 최악 시나리오에서도 하방 제한적인지

[투자 심리 참고 데이터]
{PSYCHOLOGY_CONTEXT}

위 심리 편향 데이터를 참고하여, 현재 시장 상황에서 투자자들이 빠지기 쉬운 함정이 있다면 지적하세요.

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트를 추가하지 마세요:
{{
  "signal": "매수" 또는 "매도" 또는 "관망",
  "confidence": "높음" 또는 "보통" 또는 "낮음",
  "checklist": [
    {{"item": "이해 가능한 사업인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "경제적 해자가 있는가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "합리적 가격인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "장기 보유 적합한가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "안전 마진이 있는가?", "pass": true/false, "reason": "판단 근거 한 문장"}}
  ],
  "verdict": "종합 판단 2-3문장. 초보자도 이해할 수 있게.",
  "psychology_warning": "현재 상황에서 주의해야 할 심리적 함정 한 문장 (해당 없으면 빈 문자열)"
}}""",
}

AGENT_GRAHAM = {
    "id": "graham",
    "name": "Benjamin Graham",
    "requires": ["fundamental", "market_cap", "price", "indicators"],
    "system": f"""당신은 벤저민 그레이엄의 방어적 투자 프레임워크로 판단하는 분석 에이전트입니다.
이모지를 절대 사용하지 마세요. 간결하고 명확하게 답하세요.

[판단 프레임워크 - 방어적 투자자 7가지 기준]
1. PER 15배 이하인가? - 현재 PER과 업종 평균 비교
2. PBR 1.5배 이하인가? - 자산 대비 가격 안전성
3. PER x PBR < 22.5인가? - 그레이엄의 복합 기준
4. 배당을 지급하는가? - 배당수익률과 배당 이력
5. 이익이 안정적인가? - EPS 추이, 적자 여부
6. 적정 기업 규모인가? - 시가총액이 너무 작지 않은지 (소형주 리스크)
7. 안전마진이 충분한가? - BPS 대비 현재가, 하방 리스크

[투자 심리 참고 데이터]
{PSYCHOLOGY_CONTEXT}

위 심리 편향 데이터를 참고하여, 현재 밸류에이션에서 투자자들이 빠지기 쉬운 함정이 있다면 지적하세요.

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트를 추가하지 마세요:
{{
  "signal": "매수" 또는 "매도" 또는 "관망",
  "confidence": "높음" 또는 "보통" 또는 "낮음",
  "checklist": [
    {{"item": "PER 15배 이하인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "PBR 1.5배 이하인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "PER x PBR < 22.5인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "배당을 지급하는가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "이익이 안정적인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "적정 기업 규모인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "안전마진이 충분한가?", "pass": true/false, "reason": "판단 근거 한 문장"}}
  ],
  "verdict": "종합 판단 2-3문장. 초보자도 이해할 수 있게.",
  "psychology_warning": "현재 상황에서 주의해야 할 심리적 함정 한 문장 (해당 없으면 빈 문자열)"
}}""",
}

AGENT_LYNCH = {
    "id": "lynch",
    "name": "Peter Lynch",
    "requires": ["fundamental", "market_cap", "price", "news", "indicators"],
    "system": f"""당신은 피터 린치의 성장주 투자 프레임워크로 판단하는 분석 에이전트입니다.
이모지를 절대 사용하지 마세요. 간결하고 명확하게 답하세요.

[판단 프레임워크]
1. 종목 분류 - 대형우량주/고성장주/경기순환주/턴어라운드/자산주/저성장주 중 어디에 해당?
2. PEG(PER/이익성장률) 평가 - PEG < 1이면 저평가, > 2이면 고평가
3. 성장 스토리가 있는가? - 뉴스/공시에서 성장 동력 확인
4. 기관이 관심을 갖는 종목인가? - 시가총액, 거래량으로 추정
5. 가격 위치가 적절한가? - 52주 고저 대비 현재가, RSI, 이동평균 대비

[투자 심리 참고 데이터]
{PSYCHOLOGY_CONTEXT}

위 심리 편향 데이터를 참고하여, 성장주 투자에서 특히 빠지기 쉬운 함정이 있다면 지적하세요.

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트를 추가하지 마세요:
{{
  "signal": "매수" 또는 "매도" 또는 "관망",
  "confidence": "높음" 또는 "보통" 또는 "낮음",
  "checklist": [
    {{"item": "종목 분류", "pass": true, "reason": "분류 결과와 근거 한 문장"}},
    {{"item": "PEG가 매력적인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "성장 스토리가 있는가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "적정 관심도인가?", "pass": true/false, "reason": "판단 근거 한 문장"}},
    {{"item": "가격 위치가 적절한가?", "pass": true/false, "reason": "판단 근거 한 문장"}}
  ],
  "verdict": "종합 판단 2-3문장. 초보자도 이해할 수 있게.",
  "psychology_warning": "현재 상황에서 주의해야 할 심리적 함정 한 문장 (해당 없으면 빈 문자열)"
}}""",
}

AGENTS = {
    "buffett": AGENT_BUFFETT,
    "graham": AGENT_GRAHAM,
    "lynch": AGENT_LYNCH,
}


def judge_stock(
    agent_id: str,
    stock_name: str,
    stock_data: dict,
    news_list: list | None = None,
    disclosure_list: list | None = None,
) -> dict:
    if agent_id not in AGENTS:
        return {"error": f"Unknown agent: {agent_id}"}

    if not PROVIDERS:
        return _error_result(agent_id, "API key not configured")

    agent = AGENTS[agent_id]
    data_prompt = _build_judge_prompt(
        agent, stock_name, stock_data, news_list, disclosure_list
    )

    for provider in PROVIDERS:
        try:
            client = get_client(provider)
            response = client.chat.completions.create(
                model=provider["analysis_model"],
                messages=[
                    {"role": "system", "content": agent["system"]},
                    {"role": "user", "content": data_prompt},
                ],
                max_tokens=800,
                temperature=0.4,
            )

            content = response.choices[0].message.content
            if not content or not content.strip():
                continue

            parsed = _parse_json_response(content.strip())
            if parsed:
                parsed["agent"] = agent_id
                parsed["agent_name"] = agent["name"]
                parsed["provider"] = provider["name"]
                return parsed

        except Exception as e:
            print(f"[ai_analyzer] {agent['name']} -> {provider['name']} failed: {e}")
            continue

    return _error_result(agent_id, "All providers failed")


def _build_judge_prompt(
    agent: dict,
    stock_name: str,
    stock_data: dict,
    news_list: list | None = None,
    disclosure_list: list | None = None,
) -> str:
    parts = [f"분석 대상: {stock_name}\n"]

    price = stock_data.get("price", {})
    if price.get("current_price"):
        change_sign = "+" if price.get("change_rate", 0) >= 0 else ""
        parts.append(
            f"[주가] 현재가: {price['current_price']:,}원 "
            f"({change_sign}{price.get('change_rate', 0)}%) "
            f"거래량: {price.get('volume', 0):,}"
        )

    mc = stock_data.get("market_cap", {})
    if mc.get("market_cap_text") and mc["market_cap_text"] != "-":
        parts.append(f"[시가총액] {mc['market_cap_text']}")

    fund = stock_data.get("fundamental", {})
    if fund.get("per"):
        parts.append(
            f"[재무] PER: {fund['per']}배 | PBR: {fund['pbr']}배 | "
            f"EPS: {fund['eps']:,}원 | BPS: {fund['bps']:,}원 | "
            f"배당수익률: {fund['div_yield']}%"
        )

    ind = stock_data.get("indicators", {})
    if ind.get("sma20"):
        parts.append(
            f"[기술지표] SMA5: {ind['sma5']:,} | SMA20: {ind['sma20']:,} | "
            f"SMA60: {ind['sma60']:,} | RSI14: {ind['rsi14']} | "
            f"거래량비율: {ind['volume_ratio']}x | "
            f"52주고: {ind['high_52w']:,} | 52주저: {ind['low_52w']:,}"
        )

    requires = agent.get("requires", [])

    if "news" in requires and news_list:
        news_text = "\n".join(
            [f"  - {n['title']} ({n.get('date', '')})" for n in news_list[:8]]
        )
        parts.append(f"[최근 뉴스]\n{news_text}")

    if "disclosures" in requires and disclosure_list:
        disc_text = "\n".join(
            [f"  - {d['title']} ({d.get('date', '')})" for d in disclosure_list[:5]]
        )
        parts.append(f"[최근 공시]\n{disc_text}")

    return "\n\n".join(parts)


def _parse_json_response(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    return _parse_text_fallback(text)


def _parse_text_fallback(text: str) -> dict:
    signal = "관망"
    for keyword in ["매수", "매도", "관망"]:
        if keyword in text[:200]:
            signal = keyword
            break

    return {
        "signal": signal,
        "confidence": "보통",
        "checklist": [],
        "verdict": text[:300],
        "psychology_warning": "",
    }


def _error_result(agent_id: str, reason: str) -> dict:
    return {
        "agent": agent_id,
        "agent_name": AGENTS.get(agent_id, {}).get("name", agent_id),
        "signal": "관망",
        "confidence": "낮음",
        "checklist": [],
        "verdict": f"분석을 수행할 수 없습니다: {reason}",
        "psychology_warning": "",
        "provider": "N/A",
    }
