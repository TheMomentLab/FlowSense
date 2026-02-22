<p align="center">
  <img src="static/favicon.svg" width="80" height="80" alt="FlowSense">
</p>

<h1 align="center">FlowSense</h1>

<p align="center">
  AI 기반 한국 주식 분석 플랫폼
</p>

<p align="center">
  한국어 · <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/flask-3.0-000000?style=flat&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat" alt="License">
</p>

---

FlowSense는 세 명의 전설적 투자자 -- 워런 버핏, 벤저민 그레이엄, 피터 린치 -- 의 투자 프레임워크로 한국 주식(KOSPI/KOSDAQ)을 분석합니다. 각 AI 에이전트가 실제 투자 기준을 적용해 종목을 평가하고, 심리 엔진이 개인 투자자들이 빠지기 쉬운 인지 편향을 경고합니다.

**무료 우선 아키텍처**로 설계되었습니다. Groq(무료)를 기본 LLM으로 사용하고, Gemini와 OpenAI가 폴백으로 동작합니다. 유료 API 키 없이 바로 시작할 수 있습니다.

## 기능

**AI 투자 에이전트** -- 서로 다른 프레임워크를 가진 세 에이전트. 버핏은 경제적 해자와 안전 마진을, 그레이엄은 방어적 투자 7가지 기준을, 린치는 PEG 비율과 성장 스토리를 평가합니다. 각 에이전트는 시그널, 확신도, 체크리스트, 심리 경고가 포함된 구조화된 판단을 반환합니다.

**투자 심리 경고** -- 현재 시장 상황에서 관련된 인지 편향을 탐지합니다. 앵커링, 확증 편향, 손실 회피 등 개인 투자자에게 흔한 심리적 함정을 경고합니다.

**AI 챗봇** -- 맥락 인식 스트리밍 챗봇. 메시지에서 종목명을 자동 감지하고, 실시간 데이터를 조회하여 구체적인 분석으로 응답합니다. 용어 설명, 종목 조회, 랭킹 질문을 지원합니다.

**시장 요약** -- AI가 생성하는 주간 시장 요약. 상승/하락 상위 업종 분석과 함께 업종 순환 트렌드와 시장 심리를 정리합니다.

**업종 히트맵** -- KOSPI 업종별 등락률을 시각적으로 보여줍니다. 등락률에 따라 색상이 구분되어 패턴을 빠르게 파악할 수 있습니다.

**만약에 계산기** -- "X년 Y월에 Z종목에 N원을 투자했다면 지금 얼마일까?" KRX 실제 종가 기반으로 수익률을 계산합니다.

**가상 포트폴리오** -- 1,000만원으로 시작하는 모의 투자. 실시간 가격으로 매수하고, 보유 종목과 손익을 추적합니다.

**인기 종목** -- 거래량 상위, 거래량 제로, 급상승, 급하락 종목 랭킹. KRX 실시간 데이터 기반.

## 시작하기

```bash
git clone https://github.com/TheMomentLab/FlowSense.git
cd FlowSense
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

프로젝트 루트에 `.env` 파일을 생성합니다:

```
# LLM 키 최소 1개 필요 (Groq 추천 - 무료)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# 선택: DART 공시 데이터 활성화
DART_API_KEY=your_dart_api_key
```

서버 실행:

```bash
python app.py
```

브라우저에서 `http://localhost:5000`을 엽니다.

## 구조

```
FlowSense/
├── app.py                  # Flask 앱, 라우팅, 캐싱
├── config.py               # 환경 설정, API 키 검증
├── services/
│   ├── llm_provider.py     # 멀티 LLM 프로바이더 (Groq → Gemini → OpenAI)
│   ├── ai_analyzer.py      # 3대 투자 에이전트 (버핏, 그레이엄, 린치)
│   ├── chatbot.py          # 스트리밍 챗봇 (맥락 감지)
│   ├── stock_data.py       # pykrx 기반 KRX 주가 데이터
│   ├── stock_search.py     # 종목명/코드 검색
│   ├── news_crawler.py     # 뉴스 + DART 공시 크롤러
│   └── news_cache.py       # 백그라운드 뉴스 캐싱 (스케줄러)
├── data/
│   ├── stock_list.json     # KOSPI/KOSDAQ 종목 리스트
│   └── psychology_guide.json  # 인지 편향 정의
├── templates/              # Jinja2 HTML 템플릿
└── static/                 # CSS, JS, 파비콘
```

### LLM 폴백 체인

```
요청 → Groq (무료, llama-3.3-70b) → Gemini (무료, gemini-2.0-flash) → OpenAI (유료, gpt-4o-mini)
```

각 LLM 호출은 프로바이더를 순서대로 시도합니다. 하나가 실패하면 다음이 자동으로 시도됩니다. API 키가 설정된 프로바이더만 체인에 포함됩니다.

## API 레퍼런스

| 메서드 | 엔드포인트 | 설명 |
|--------|----------|------|
| GET | `/api/search?q=` | 종목명 검색 |
| GET | `/api/stock?name=` | 종목 전체 데이터 (주가, 재무, 지표, 뉴스) |
| GET | `/api/stock/summary?code=` | AI 한줄 요약 |
| GET | `/api/judge?agent=&name=` | AI 에이전트 분석 (buffett, graham, lynch) |
| GET | `/api/chat?message=&stock=` | 스트리밍 챗봇 (SSE) |
| GET | `/api/popular?limit=&category=` | 인기 종목 (volume_top, top_gainers, top_losers, volume_zero) |
| GET | `/api/sectors` | KOSPI 업종별 등락률 |
| GET | `/api/digest` | AI 주간 시장 요약 |
| GET | `/api/whatif?name=&amount=&date=` | 과거 투자 수익률 계산 |
| GET | `/api/cache/status` | 뉴스 캐시 상태 |
| POST | `/api/cache/update` | 백그라운드 캐시 업데이트 |

## 환경 변수

| 변수 | 필수 여부 | 설명 |
|------|----------|------|
| `GROQ_API_KEY` | LLM 키 최소 1개 | Groq API 키 (groq.com에서 무료 발급) |
| `GEMINI_API_KEY` | LLM 키 최소 1개 | Google Gemini API 키 |
| `OPENAI_API_KEY` | LLM 키 최소 1개 | OpenAI API 키 |
| `DART_API_KEY` | 아니오 | OpenDART API 키 (기업 공시용) |
| `FLASK_ENV` | 아니오 | `development` 설정 시 디버그 모드 |

## 기술 스택

- **백엔드**: Flask 3.0, APScheduler
- **AI**: OpenAI SDK (Groq, Gemini, OpenAI 호환)
- **시장 데이터**: pykrx (한국거래소), BeautifulSoup4 (뉴스 크롤링)
- **공시**: OpenDART API
- **프론트엔드**: Vanilla JS, CSS (프레임워크 없음)

## 라이선스

MIT

---

본 서비스는 정보 제공 목적이며, 투자 권유가 아닙니다. 실제 투자 결정은 전문가와 상담하시기 바랍니다.
