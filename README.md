<p align="center">
  <img src="static/favicon.svg" width="80" height="80" alt="FlowSense">
</p>

<h1 align="center">FlowSense</h1>

<p align="center">
  AI-powered Korean stock market analysis platform
</p>

<p align="center">
  <a href="README.ko.md">한국어</a> · English
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/flask-3.0-000000?style=flat&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat" alt="License">
</p>

---

FlowSense analyzes Korean stocks (KOSPI/KOSDAQ) through the lens of three legendary investors — Warren Buffett, Benjamin Graham, and Peter Lynch. Each AI agent applies their real investment framework to evaluate stocks, while a psychology engine warns about cognitive biases that trap retail investors.

Built with a **free-first architecture**: Groq (free) is the primary LLM, with Gemini and OpenAI as fallbacks. No paid API key required to get started.

## Features

**AI Investment Agents** — Three agents with distinct frameworks. Buffett checks for economic moats and margin of safety. Graham applies his defensive 7-criteria screen. Lynch evaluates PEG ratios and growth stories. Each returns a structured verdict with signal, confidence, checklist, and psychology warning.

**Investment Psychology Warnings** — Detects cognitive biases relevant to current market conditions. Warns about anchoring, confirmation bias, loss aversion, and other traps that commonly affect retail investors.

**AI Chatbot** — Context-aware streaming chatbot. Automatically detects stock names in messages, fetches real-time data, and responds with concrete analysis. Supports term explanations, stock queries, and ranking questions.

**Market Digest** — AI-generated weekly market summary with top/bottom sector analysis. Identifies sector rotation trends and summarizes market sentiment.

**Sector Heatmap** — Visual overview of KOSPI sector performance. Color-coded by change rate for quick pattern recognition.

**What-If Calculator** — "If I invested X won in Y stock on Z date, how much would it be worth today?" Calculates actual returns based on historical KRX closing prices.

**Virtual Portfolio** — Paper trading with 10M KRW starting balance. Buy stocks at real-time prices, track holdings, and monitor profit/loss.

**Popular Stocks** — Rankings by volume (top and zero-volume), top gainers, and top losers. Updated from live KRX data.

## Quick Start

```bash
git clone https://github.com/TheMomentLab/FlowSense.git
cd FlowSense
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
# At least one LLM key required (Groq recommended - free)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# Optional: enables disclosure data from DART
DART_API_KEY=your_dart_api_key
```

Run the server:

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

## Architecture

```
FlowSense/
├── app.py                  # Flask application, routes, caching
├── config.py               # Environment config, API key validation
├── services/
│   ├── llm_provider.py     # Multi-LLM provider (Groq → Gemini → OpenAI)
│   ├── ai_analyzer.py      # 3 investment agents (Buffett, Graham, Lynch)
│   ├── chatbot.py          # Streaming chatbot with context detection
│   ├── stock_data.py       # KRX stock data via pykrx
│   ├── stock_search.py     # Stock name/code search
│   ├── news_crawler.py     # News + DART disclosure crawler
│   └── news_cache.py       # Background news caching with scheduler
├── data/
│   ├── stock_list.json     # KOSPI/KOSDAQ stock list
│   └── psychology_guide.json  # Cognitive bias definitions
├── templates/              # Jinja2 HTML templates
└── static/                 # CSS, JS, favicon
```

### LLM Fallback Chain

```
Request → Groq (free, llama-3.3-70b) → Gemini (free tier, gemini-2.0-flash) → OpenAI (paid, gpt-4o-mini)
```

Each LLM call attempts providers in order. If one fails, the next is tried automatically. Only configured providers (with API keys) are included in the chain.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=` | Search stocks by name |
| GET | `/api/stock?name=` | Full stock data (price, fundamentals, indicators, news) |
| GET | `/api/stock/summary?code=` | AI one-line summary |
| GET | `/api/judge?agent=&name=` | AI agent analysis (buffett, graham, lynch) |
| GET | `/api/chat?message=&stock=` | Streaming chatbot (SSE) |
| GET | `/api/popular?limit=&category=` | Popular stocks (volume_top, top_gainers, top_losers, volume_zero) |
| GET | `/api/sectors` | KOSPI sector performance |
| GET | `/api/digest` | AI weekly market digest |
| GET | `/api/whatif?name=&amount=&date=` | Historical return calculator |
| GET | `/api/cache/status` | News cache status |
| POST | `/api/cache/update` | Trigger background cache update |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | At least one LLM key | Groq API key (free at groq.com) |
| `GEMINI_API_KEY` | At least one LLM key | Google Gemini API key |
| `OPENAI_API_KEY` | At least one LLM key | OpenAI API key |
| `DART_API_KEY` | No | OpenDART API key for corporate disclosures |
| `FLASK_ENV` | No | Set to `development` for debug mode |

## Tech Stack

- **Backend**: Flask 3.0, APScheduler
- **AI**: OpenAI SDK (compatible with Groq, Gemini, OpenAI)
- **Market Data**: pykrx (Korea Exchange), BeautifulSoup4 (news crawling)
- **Disclosures**: OpenDART API
- **Frontend**: Vanilla JS, CSS (no framework)

## License

MIT

---

This service is for informational purposes only and does not constitute investment advice. Please consult a qualified financial advisor before making investment decisions.
