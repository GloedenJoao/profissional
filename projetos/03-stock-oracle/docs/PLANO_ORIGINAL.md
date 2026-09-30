# Stock Oracle — Implementation Plan

## Project Goal
Local webapp where multiple specialized AI agents make stock price predictions, tracked against real prices to benchmark agent accuracy. Educational goal: learning to measure AI agent performance with verifiable ground truth (next-day actual price).

---

## Tech Stack
- **Backend**: FastAPI (asyncio parallelism for parallel agent calls)
- **Frontend**: Jinja2 templates + Bootstrap 5 CDN + Chart.js CDN
- **Storage**: SQLite via SQLAlchemy
- **Stock data**: yfinance (free, no API key)
- **News data**: Google News RSS via feedparser (free, no API key)
- **Claude API**: `anthropic` Python SDK, model `claude-opus-4-8`, adaptive thinking
- **Tests**: pytest + pytest-asyncio + pytest-cov

---

## Agents
| Agent | Role |
|---|---|
| `HistoricalAgent` | Analyzes 90-day price patterns, RSI, MACD, SMA, volatility |
| `SentimentAgent` | Analyzes recent news headlines from Google News RSS |
| `FundamentalsAgent` | Analyzes P/E, revenue growth, debt/equity, market cap via yfinance |
| `OrchestratorAgent` | Consolidates all agent outputs into final prediction |
| `EvaluatorAgent` | Resolves open predictions against actual prices (daily scheduled job) |

All specialist agents extend `BaseAgent`, implement `_fetch_data()` and `_build_prompt()`.  
Adding a new agent: create file, add to `AGENT_REGISTRY` dict — appears automatically in UI.

---

## Directory Structure

```
stock_oracle/
├── PLAN.md                          ← this file
├── CLAUDE.md                        ← project overview
├── pyproject.toml                   ← all deps
├── .env.example                     ← ANTHROPIC_API_KEY=...
├── .gitignore
│
├── app/
│   ├── CLAUDE.md                    ← layer separation rules
│   ├── __init__.py
│   ├── main.py                      ← FastAPI factory + APScheduler lifespan
│   ├── config.py                    ← Pydantic BaseSettings, reads .env
│   ├── database.py                  ← engine, SessionLocal, get_db()
│   │
│   ├── models/
│   │   ├── CLAUDE.md
│   │   ├── __init__.py
│   │   ├── stock.py                 ← Stock, ActualPrice tables
│   │   ├── prediction.py            ← Prediction, AgentPrediction tables
│   │   └── metrics.py               ← AgentMetrics snapshot table
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── prediction.py            ← PredictionCreate, PredictionOut, AgentPredictionOut
│   │   └── metrics.py               ← AgentMetricsOut, PerformanceSummary
│   │
│   ├── agents/
│   │   ├── CLAUDE.md                ← BaseAgent contract + how-to-add guide
│   │   ├── __init__.py
│   │   ├── base.py                  ← BaseAgent ABC, AgentInput/AgentOutput dataclasses
│   │   ├── historical.py
│   │   ├── sentiment.py
│   │   ├── fundamentals.py
│   │   ├── orchestrator.py          ← different interface: synthesize(List[AgentOutput])
│   │   ├── evaluator.py             ← resolves predictions, no Claude call
│   │   └── registry.py              ← AGENT_REGISTRY dict + get_agent() factory
│   │
│   ├── data/
│   │   ├── CLAUDE.md
│   │   ├── __init__.py
│   │   ├── fetchers/
│   │   │   ├── price.py             ← get_current_price(), get_price_history(), get_actual_close()
│   │   │   ├── news.py              ← get_news_headlines() via feedparser + Google News RSS
│   │   │   └── fundamentals.py      ← get_fundamentals() via yfinance .info
│   │   └── processors/
│   │       └── technical.py         ← compute_indicators(): RSI, MACD, SMA20/50, EMA, volatility
│   │
│   ├── routers/
│   │   ├── pages.py                 ← GET / /new /performance /prediction/{id}
│   │   ├── predictions.py           ← POST /api/predictions, GET /api/predictions/{id}
│   │   └── metrics.py               ← GET /api/metrics, POST /api/evaluate
│   │
│   ├── services/
│   │   ├── prediction_service.py    ← run_pipeline(): parallel agents → orchestrator → DB
│   │   ├── evaluation_service.py    ← run_evaluation(): fetch actuals, mark resolved
│   │   └── metrics_service.py       ← compute_metrics(): MAE/MAPE/directional accuracy
│   │
│   └── templates/
│       ├── base.html
│       ├── dashboard.html           ← open + recent resolved predictions
│       ├── new_prediction.html      ← form: ticker + agent checkboxes
│       ├── agent_performance.html   ← metrics table + Chart.js charts
│       └── prediction_detail.html   ← per-agent reasoning accordions
│
├── static/
│   ├── css/app.css
│   └── js/charts.js
│
├── tests/
│   ├── CLAUDE.md
│   ├── conftest.py                  ← test_db, mock_claude_client, sample_aapl_data fixtures
│   ├── test_agents/
│   ├── test_data/
│   ├── test_routers/
│   └── test_services/
│
└── scripts/
    ├── init_db.py                   ← Base.metadata.create_all()
    └── run_evaluation.py            ← manual evaluation trigger
```

---

## Data Models

### `stocks`
| Column | Type | Notes |
|---|---|---|
| `ticker` | String(10) | PK |
| `name` | String(200) | nullable |
| `sector` | String(100) | nullable |
| `created_at` | DateTime | default=now() |

### `actual_prices`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer | PK |
| `ticker` | String(10) | FK→stocks |
| `price_date` | Date | not null |
| `close_price` | Float | not null |
| `fetched_at` | DateTime | default=now() |

UniqueConstraint: `(ticker, price_date)`

### `predictions`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer | PK |
| `ticker` | String(10) | FK→stocks |
| `created_at` | DateTime | |
| `target_date` | Date | |
| `status` | String(20) | `"open"` or `"resolved"` |
| `agents_used` | Text | JSON-encoded list |
| `orchestrator_predicted_price` | Float | |
| `orchestrator_predicted_direction` | String(10) | `"up"` or `"down"` |
| `orchestrator_confidence` | Float | 0.0–1.0 |
| `orchestrator_reasoning` | Text | |
| `actual_price` | Float | null until resolved |
| `actual_direction` | String(10) | null until resolved |
| `resolved_at` | DateTime | null until resolved |

### `agent_predictions`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer | PK |
| `prediction_id` | Integer | FK→predictions |
| `agent_name` | String(50) | |
| `predicted_price` | Float | |
| `predicted_direction` | String(10) | |
| `confidence` | Float | |
| `reasoning` | Text | |
| `prompt_tokens_used` | Integer | nullable |
| `created_at` | DateTime | |

UniqueConstraint: `(prediction_id, agent_name)`

### `agent_metrics` (snapshot/cache)
| Column | Type | Notes |
|---|---|---|
| `id` | Integer | PK |
| `agent_name` | String(50) | indexed |
| `computed_at` | DateTime | |
| `prediction_count` | Integer | |
| `resolved_count` | Integer | |
| `directional_accuracy` | Float | null if 0 resolved |
| `mae` | Float | null if 0 resolved |
| `mape` | Float | null if 0 resolved |
| `rolling_30d_directional_accuracy` | Float | |
| `rolling_30d_count` | Integer | |

---

## Agent Architecture

### BaseAgent (all specialist agents extend this)
```python
@dataclass
class AgentInput:
    ticker: str
    current_price: float
    target_date: date
    payload: dict = field(default_factory=dict)

@dataclass
class AgentOutput:
    agent_name: str
    predicted_price: float
    predicted_direction: str   # "up" | "down"
    confidence: float          # 0.0–1.0
    reasoning: str
    prompt_tokens_used: int
```

Claude API call shape (confirmed correct):
```python
response = await self._client.messages.create(
    model="claude-opus-4-8",
    max_tokens=8192,
    thinking={"type": "adaptive"},
    output_config={
        "format": {
            "type": "json_schema",
            "schema": { ... }
        }
    },
    messages=[{"role": "user", "content": prompt}]
)
text_block = next(b for b in response.content if b.type == "text")
data = json.loads(text_block.text)
```

Note: No `messages.parse()` method exists in the SDK. Parse manually via `json.loads`.

### Prediction Pipeline Flow
```
POST /api/predictions
  └─ prediction_service.run_pipeline()
       ├─ get_current_price(ticker)
       ├─ asyncio.gather(
       │     historical.predict(),
       │     sentiment.predict(),
       │     fundamentals.predict(),
       │  )  ← parallel Claude calls
       ├─ orchestrator.synthesize(agent_outputs)  ← sequential, after all 3
       └─ DB write (Prediction + AgentPredictions)

POST /api/evaluate (or APScheduler daily 16:30 ET)
  └─ evaluation_service.run_evaluation()
       └─ evaluator.evaluate()
            ├─ fetch actual prices from yfinance
            ├─ update predictions.status = "resolved"
            └─ upsert into actual_prices
```

---

## Metrics
- **Directional accuracy**: `correct_direction_count / resolved_count`
- **MAE**: `mean(abs(predicted - actual))`
- **MAPE**: `mean(abs(predicted - actual) / actual)` → display as %
- **Rolling 30d**: filter `predictions.created_at >= now - 30d`
- Computed live in `metrics_service.py`, snapshot stored in `agent_metrics`

---

## Implementation Phases

| Phase | Goal | Key files |
|---|---|---|
| **1** | App starts, DB initializes, homepage renders | `pyproject.toml`, `config.py`, `database.py`, all models, `scripts/init_db.py`, `base.html`, `main.py` |
| **2** | Real data fetchable for any ticker | `data/fetchers/price.py`, `news.py`, `fundamentals.py`, `data/processors/technical.py` |
| **3** | First Claude API call → structured prediction | `agents/base.py`, `agents/historical.py` |
| **4** | All specialist agents work individually | `sentiment.py`, `fundamentals.py`, `registry.py` |
| **5** | Full pipeline: form → prediction → DB | `orchestrator.py`, `prediction_service.py`, `routers/predictions.py`, `new_prediction.html` |
| **6** | Evaluation + metrics | `evaluator.py`, `evaluation_service.py`, `metrics_service.py`, `routers/metrics.py` |
| **7** | Full frontend (all 4 pages) | All templates, `charts.js` |
| **8** | Tests ≥80% coverage | All `tests/` files |

---

## Test Strategy

**Mock policy**: Always mock Claude API (`AsyncMock`), yfinance, and feedparser. Never make real API calls in tests.

**Three core fixtures** (`tests/conftest.py`):
1. `test_db` — in-memory SQLite, auto-teardown, overrides `get_db` for route tests
2. `mock_claude_client` — returns deterministic `AgentOutput` from mocked `messages.create`
3. `sample_aapl_data` — fixed OHLCV + indicators + headlines dict

**Test layers**:
| Layer | Type | External deps mocked? |
|---|---|---|
| `technical.py` RSI/MACD math | Unit | No (pure pandas/numpy) |
| Price/news/fundamentals fetchers | Unit | Yes (yfinance, feedparser) |
| Agent `_build_prompt()` | Unit | No (pure string formatting) |
| Agent `_call_claude()` | Unit | Yes (AsyncAnthropic) |
| `metrics_service.compute_metrics()` | Integration | No (in-memory SQLite) |
| API routes | Integration | Yes + TestClient + in-memory DB |

---

## `pyproject.toml` (complete)
```toml
[project]
name = "stock-oracle"
version = "0.1.0"
description = "Multi-agent stock price prediction webapp for AI agent benchmarking"
requires-python = ">=3.10"
dependencies = [
    "anthropic>=0.109.2",
    "fastapi>=0.137.1",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy>=2.0.51",
    "pydantic-settings>=2.7.0",
    "yfinance>=1.4.1",
    "feedparser>=6.0.12",
    "apscheduler>=3.11.2",
    "python-multipart>=0.0.20",
    "jinja2>=3.1.0",
    "pandas>=2.2.0",
    "numpy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Next Session: Start Here

Run Phase 1 in order:
1. Create `pyproject.toml` (content above)
2. Create `.env.example` with `ANTHROPIC_API_KEY=your_key_here`
3. Create `app/config.py`, `app/database.py`
4. Create all model files (`app/models/stock.py`, `prediction.py`, `metrics.py`, `__init__.py`)
5. Create `scripts/init_db.py`
6. Create `app/templates/base.html` (Bootstrap 5 + Chart.js CDN)
7. Create `app/routers/pages.py` (single GET `/` route)
8. Create `app/main.py` (FastAPI factory)
9. Run `python scripts/init_db.py` → creates `stock_oracle.db`
10. Run `uvicorn app.main:app --reload` → homepage loads
