# Filing Intelligence Project Plan

## 1. Product Goal

Build a production-ready platform that:

1. Tracks S&P 500 companies.
2. Fetches each company's 10-Q filings through `sec-api.io`.
3. Extracts high-value sections such as MD&A and Risk Factors.
4. Uses OpenAI models to generate structured investor insights.
5. Stores raw filings, extracted sections, and AI outputs for comparison, trend analysis, and dashboards.
6. Optionally correlates filing tone/themes with post-filing stock-price moves.

This document assumes a greenfield build in the current repository.

## 2. Recommended Stack

### Backend choice: Python + Flask

Choose `Python/Flask` over `Node.js/Express`.

Reasoning:

- Python is the better fit for ETL-style workflows, NLP-heavy preprocessing, finance text handling, and AI orchestration.
- The OpenAI Python SDK, validation libraries, and data tooling make chunking, structured outputs, batch jobs, and offline analysis simpler.
- Flask is lightweight and stable for REST APIs, and pairs well with SQLAlchemy, Celery, Redis, and Gunicorn.
- The system will be worker-heavy more than request-heavy, so backend ergonomics for data pipelines matter more than frontend symmetry.

Recommended Python stack:

- `Flask` for the API layer
- `SQLAlchemy` + `Alembic` for ORM and migrations
- `Celery` + `Redis` for background processing
- `httpx` for external API calls
- `pydantic` for request/response and AI schema validation
- `tenacity` for retries and backoff
- `gunicorn` for production serving

### Database choice: PostgreSQL

Choose `PostgreSQL` over `MongoDB`.

Reasoning:

- Filing insights are structured and relational: company -> filing -> section -> AI run -> insight -> price window.
- PostgreSQL is better for filtering, aggregations, joins, trending queries, and time-series-like analysis.
- `JSONB` gives flexibility for raw SEC metadata, AI traces, and theme payloads without giving up relational integrity.
- Materialized views and indexes make dashboard queries fast.

Add supporting stores:

- `Redis` for rate limiting, Celery broker/cache, and transient job state
- `S3-compatible object storage` for immutable raw filing payloads, extracted sections, and exported datasets

### AI choice: OpenAI Responses API

Recommended model strategy:

- Default filing analysis: `gpt-5.4-mini`
- High-confidence or premium reprocessing: `gpt-5.4`
- Simple high-volume classification or tagging: `gpt-5.4-nano`

Why:

- OpenAI currently recommends starting with `gpt-5.4` for complex reasoning/coding, with `gpt-5.4-mini` and `gpt-5.4-nano` for lower-cost workloads.
- Latest OpenAI models support the `Responses API` and Structured Outputs, which is ideal for typed investor insight objects.

Important implementation choices:

- Use the `Responses API`
- Use Structured Outputs with JSON schema
- Use `Batch API` for backfills and reprocessing
- Use `background=true` for long-running responses when synchronous timeouts are a risk
- Use prompt caching for repeated prompt prefixes and stable schemas

### Frontend choice

- `React` + `Vite`
- `TailwindCSS`
- `TanStack Query` for API state
- `React Router`
- `Recharts` or `Nivo` for charts
- `AG Grid` or `TanStack Table` for dense filing comparisons

### Market data choice

Default recommendation: `Polygon.io`

Why:

- Better fit for production event studies and richer U.S. equities coverage
- Stronger API and flat-file options for historical analysis

Fallback budget option: `Alpha Vantage`

Why:

- Good for a lower-cost proof of concept
- But the free tier is much more restrictive and many useful endpoints are premium-only

## 3. Important Data Source Notes

### SEC-API design notes

Use `sec-api.io` in two modes:

- `Query API` for initial backfill and targeted historical fetches
- `Stream API` for near-real-time monitoring of newly filed 10-Qs

Use `Extractor API` for section extraction instead of sending entire filings into the model.

For 10-Qs, the key extractor item codes are:

- `part1item2` -> MD&A
- `part2item1a` -> Risk Factors
- `part1item1` -> Financial Statements
- `part1item3` -> Quantitative and Qualitative Disclosures About Market Risk
- `part2item1` -> Legal Proceedings

Critical deduplication rule:

- Deduplicate filings by `accessionNo`, not by sec-api's internal `id`
- A filing may reference multiple entities and create multiple metadata objects

### S&P 500 universe note

S&P 500 constituent data is not the same thing as general listed-company metadata. In production, do not rely on ad hoc scraping for the official universe.

Recommended approach:

1. Maintain a versioned `sp500_constituents.csv` in the repo or database as a controlled source.
2. Refresh it from a licensed or approved data source on a scheduled cadence.
3. Map tickers to CIK/company metadata through sec-api's Mapping API.

## 4. High-Level Architecture

```text
Constituent Sync
  -> companies table
  -> filing discovery jobs

Filing Discovery
  -> sec-api Query API / Stream API
  -> filings table
  -> raw metadata in object storage

Section Extraction
  -> sec-api Extractor API
  -> filing_sections table
  -> raw section text/html in object storage

AI Analysis Pipeline
  -> chunking / preprocessing
  -> section-level summaries
  -> filing-level synthesis
  -> filing_insights + theme_mentions + ai_runs

Price Correlation
  -> Polygon / Alpha Vantage
  -> price_windows table

API Layer
  -> dashboards / filters / compare endpoints

React Frontend
  -> company explorer
  -> filing detail
  -> quarter-over-quarter compare
  -> theme and sentiment trends
```

## 5. Suggested Repository Structure

```text
sec-filing-analyzer/
  apps/
    api/
      app.py
      config.py
      extensions.py
      routes/
        health.py
        companies.py
        filings.py
        insights.py
        compare.py
        jobs.py
      services/
        company_service.py
        filing_service.py
        extraction_service.py
        insight_service.py
        pricing_service.py
        analytics_service.py
      clients/
        sec_api_client.py
        openai_client.py
        market_data_client.py
      models/
        company.py
        filing.py
        filing_section.py
        ai_run.py
        filing_insight.py
        theme_mention.py
        price_window.py
        job.py
      schemas/
        company.py
        filing.py
        insight.py
        compare.py
      prompts/
        filing_summary_v1.md
        section_summary_v1.md
      utils/
        chunking.py
        hashing.py
        logging.py
        rate_limit.py
        trading_calendar.py
      tests/
        unit/
        integration/
    worker/
      celery_app.py
      tasks/
        sync_universe.py
        discover_filings.py
        extract_sections.py
        analyze_filing.py
        correlate_prices.py
        reprocess_filing.py
  web/
    src/
      app/
      api/
      components/
      features/
        companies/
        filings/
        compare/
        trends/
      pages/
        DashboardPage.tsx
        CompanyPage.tsx
        FilingDetailPage.tsx
        ComparePage.tsx
        TrendsPage.tsx
      styles/
      lib/
  infra/
    docker/
    terraform/
    github-actions/
  scripts/
    bootstrap_sp500.py
    backfill_10q.py
    reprocess_low_confidence.py
  docs/
    data-contracts.md
    prompt-versions.md
    runbooks.md
  alembic/
  .env.example
  docker-compose.yml
  PROJECT_PLAN.md
```

## 6. End-to-End Data Flow

### Phase A: Company universe sync

1. Load approved S&P 500 constituent list.
2. Resolve each ticker to CIK, company name, sector, industry, exchange, and security category.
3. Store companies in `companies`.
4. Mark active/inactive membership dates for historical consistency.

### Phase B: Filing discovery

1. For backfill, query sec-api Query API by `cik` or ticker and `formType:"10-Q"`.
2. Slice by `filedAt` month or quarter to avoid large result sets.
3. Persist filing metadata and raw API response.
4. Deduplicate by `accessionNo`.
5. Mark newly discovered filings for extraction.

### Phase C: Section extraction

1. Use the filing URL from sec-api metadata.
2. Extract `part1item2` and `part2item1a` first.
3. Optionally extract `part1item1`, `part1item3`, and `part2item1`.
4. Save raw text, HTML, hashes, and word counts.
5. Flag extraction errors or empty sections for review.

### Phase D: AI analysis

1. Clean section text:
   - Normalize whitespace
   - Remove boilerplate where safe
   - Preserve evidence snippets and section boundaries
2. Chunk long sections by heading and token budget.
3. Run section-level summaries in parallel.
4. Run a second filing-level synthesis over the section summaries.
5. Validate model output against a strict JSON schema.
6. Store insights, evidence, token usage, model version, and prompt version.

### Phase E: Price correlation

1. Normalize filing time using `filedAt` in Eastern Time.
2. Determine the event window anchor:
   - If filed during market hours, anchor same-day close
   - If filed after market close, anchor next trading day open/close depending on study design
3. Fetch returns for `T+1`, `T+5`, `T+20` and benchmark returns, e.g. `SPY`.
4. Store simple returns and abnormal returns.

### Phase F: Serving analytics

1. API exposes filtered filings and insights.
2. Frontend shows latest, historical, and cross-company comparisons.
3. Materialized views or precomputed rollups power fast dashboards.

## 7. Core Database Schema

### `companies`

```sql
id uuid primary key
ticker varchar(16) not null
cik varchar(20) not null
name text not null
sector text null
industry text null
exchange text null
security_category text null
sp500_active boolean not null default true
sp500_added_at date null
sp500_removed_at date null
created_at timestamptz not null
updated_at timestamptz not null

unique (ticker)
unique (cik)
```

### `filings`

```sql
id uuid primary key
company_id uuid not null references companies(id)
accession_no varchar(32) not null
form_type varchar(16) not null
filed_at timestamptz not null
period_of_report date null
fiscal_year int null
fiscal_quarter int null
link_to_html text null
link_to_txt text null
link_to_filing_details text not null
source_payload jsonb not null
ingestion_status varchar(32) not null
is_amendment boolean not null default false
supersedes_filing_id uuid null references filings(id)
created_at timestamptz not null
updated_at timestamptz not null

unique (accession_no)
index (company_id, filed_at desc)
index (form_type, filed_at desc)
```

### `filing_sections`

```sql
id uuid primary key
filing_id uuid not null references filings(id)
section_code varchar(32) not null
section_name text not null
content_text text null
content_html text null
content_hash varchar(64) not null
word_count int not null default 0
token_estimate int not null default 0
extraction_status varchar(32) not null
created_at timestamptz not null
updated_at timestamptz not null

unique (filing_id, section_code)
index (content_hash)
```

### `ai_runs`

```sql
id uuid primary key
filing_id uuid not null references filings(id)
run_type varchar(32) not null
model_name varchar(64) not null
prompt_version varchar(32) not null
schema_version varchar(32) not null
status varchar(32) not null
input_tokens int null
cached_tokens int null
output_tokens int null
estimated_cost_usd numeric(12, 6) null
raw_response jsonb null
error_message text null
started_at timestamptz null
completed_at timestamptz null
created_at timestamptz not null
```

### `filing_insights`

```sql
id uuid primary key
filing_id uuid not null references filings(id)
ai_run_id uuid not null references ai_runs(id)
executive_summary text not null
investor_pros jsonb not null
investor_cons jsonb not null
sentiment varchar(16) not null
sentiment_score numeric(4, 3) not null
themes jsonb not null
key_risks jsonb not null
key_opportunities jsonb not null
notable_changes_vs_prior jsonb null
confidence numeric(4, 3) not null
created_at timestamptz not null

unique (filing_id, ai_run_id)
index (sentiment)
```

### `theme_mentions`

```sql
id uuid primary key
filing_insight_id uuid not null references filing_insights(id)
theme_key varchar(64) not null
direction varchar(16) not null
strength numeric(4, 3) not null
section_code varchar(32) not null
evidence_excerpt text not null
created_at timestamptz not null

index (theme_key)
index (theme_key, created_at desc)
```

### `price_windows`

```sql
id uuid primary key
filing_id uuid not null references filings(id)
company_id uuid not null references companies(id)
provider varchar(32) not null
benchmark_symbol varchar(16) not null default 'SPY'
event_anchor_timestamptz timestamptz not null
pre_1d_return numeric(10, 6) null
post_1d_return numeric(10, 6) null
post_5d_return numeric(10, 6) null
post_20d_return numeric(10, 6) null
benchmark_post_1d_return numeric(10, 6) null
benchmark_post_5d_return numeric(10, 6) null
benchmark_post_20d_return numeric(10, 6) null
abnormal_post_1d_return numeric(10, 6) null
abnormal_post_5d_return numeric(10, 6) null
abnormal_post_20d_return numeric(10, 6) null
created_at timestamptz not null

unique (filing_id, provider)
```

### `jobs`

```sql
id uuid primary key
job_type varchar(32) not null
status varchar(32) not null
payload jsonb not null
result jsonb null
retry_count int not null default 0
error_message text null
created_at timestamptz not null
updated_at timestamptz not null

index (job_type, status)
```

## 8. AI Output Contract

Use a strict JSON schema so every filing produces a typed object.

Suggested top-level contract:

```json
{
  "executive_summary": "string",
  "investor_pros": ["string"],
  "investor_cons": ["string"],
  "sentiment": "bullish | bearish | neutral",
  "sentiment_score": 0.12,
  "themes": [
    {
      "theme": "growth",
      "direction": "positive | negative | mixed",
      "strength": 0.82,
      "summary": "string",
      "evidence": [
        {
          "section_code": "part1item2",
          "excerpt": "string"
        }
      ]
    }
  ],
  "key_risks": ["string"],
  "key_opportunities": ["string"],
  "notable_changes_vs_prior": ["string"],
  "confidence": 0.87
}
```

Theme taxonomy:

- `growth`
- `cost_pressures`
- `macro_exposure`
- `regulatory_risk`
- `innovation`

Optional extensions:

- `demand_trends`
- `pricing_power`
- `margin_pressure`
- `capital_allocation`
- `supply_chain`
- `geopolitical_risk`

## 9. Backend API Endpoints

### Health and ops

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/jobs/:job_id`

### Companies

- `GET /api/v1/companies`
- `GET /api/v1/companies/:ticker`
- `POST /api/v1/companies/sync`

### Filings

- `GET /api/v1/filings?tickers=AAPL,MSFT&from=2025-01-01&to=2025-12-31`
- `GET /api/v1/filings/:filing_id`
- `POST /api/v1/filings/sync`
- `POST /api/v1/filings/:filing_id/reprocess`

### Insights and analytics

- `GET /api/v1/insights/latest`
- `GET /api/v1/insights/:filing_id`
- `GET /api/v1/companies/:ticker/trends`
- `GET /api/v1/themes/trends`
- `GET /api/v1/sentiment/overview`
- `GET /api/v1/compare?tickers=AAPL,MSFT&periods=2025Q1,2024Q1`

### Price study

- `POST /api/v1/prices/sync`
- `GET /api/v1/prices/:filing_id`

## 10. Frontend Screens

### 1. Dashboard

Show:

- Latest 10-Q filings processed
- Sentiment distribution
- Theme frequency over the latest quarter
- Companies with largest sentiment shifts
- Recent filings awaiting review or failed extraction

### 2. Company page

Show:

- Company profile
- Filing history table
- Quarter-over-quarter executive summaries
- Theme trend chart
- Sentiment timeline
- Price reaction summary

### 3. Filing detail page

Show:

- Filing metadata
- Executive summary
- Investor pros and cons
- Theme cards with evidence
- Risk Factors excerpted evidence
- MD&A section summaries
- Price move panel

### 4. Compare page

Show:

- Side-by-side comparison across companies or quarters
- Theme overlap and divergence
- Sentiment delta
- MD&A summary delta
- Risk Factors delta

### 5. Trends page

Show:

- Theme heatmap by sector
- Sentiment by quarter
- Top recurring risks
- Growth vs cost-pressure trend lines

## 11. Best Practices for Large Filing Processing

### Primary optimization

Never send the full raw filing to the model unless absolutely necessary.

Instead:

1. Use sec-api Extractor API to isolate only relevant sections.
2. Chunk long sections by heading and token count.
3. Summarize chunks in parallel.
4. Synthesize chunk summaries into one filing-level insight object.

### Chunking strategy

Recommended rules:

- Chunk on heading boundaries first
- Hard cap chunks around 6k to 10k tokens each
- Preserve section metadata with every chunk
- Remove repetitive table markup unless the table is clearly material
- Keep a rolling evidence map of sentence offsets

### Parallelization

- Parallelize section extraction per filing
- Parallelize chunk-level summaries within a filing
- Cap concurrency with a Redis-backed semaphore to protect external APIs
- Use Celery routing so extraction and AI analysis can scale independently

### Cost optimization

- Use `gpt-5.4-mini` for standard analysis
- Use `Batch API` for historical backfills
- Use prompt caching with stable system prompts and schemas
- Skip re-analysis if `content_hash` has not changed
- Reuse prior-quarter derived summaries when generating deltas

### Reliability optimization

- Use OpenAI `background=true` for long-running filings
- Persist intermediate section summaries before filing-level synthesis
- Retry only idempotent steps
- Keep dead-letter queues for repeatedly failing filings

## 12. Rate Limiting, Caching, and Error Handling

### External API protection

Implement a provider abstraction with:

- per-provider timeout config
- per-provider retry policy
- per-provider concurrency limit
- global circuit breaker

Recommended retry policy:

- Retry on `429`, `500`, `502`, `503`, `504`
- Exponential backoff with jitter
- Max 3 to 5 attempts
- Log provider latency and failure rate

### Caching strategy

Cache layers:

1. `Redis`
   - hot API responses
   - job state
   - rate-limit counters
2. `PostgreSQL`
   - canonical metadata and insights
3. `Object storage`
   - immutable raw filing metadata
   - raw extracted sections
   - exported reports and evaluation sets

Immutable object keys should include:

- provider
- accession number
- section code
- hash or version

### Idempotency rules

- `accessionNo` is the canonical filing identity
- `filing_id + section_code` is the canonical section identity
- `content_hash + prompt_version + schema_version + model_name` is the canonical AI run identity

### Failure states to model explicitly

- discovery failed
- extraction failed
- empty section
- ai validation failed
- ai timeout
- pricing fetch failed
- comparison unavailable

## 13. Security and Production Hardening

- Keep all API keys in environment variables or a secrets manager
- Never expose sec-api or OpenAI keys to the browser
- Add request authentication for internal admin endpoints
- Sanitize and length-limit all user-supplied filters
- Log audit events for reprocess and backfill jobs
- Use row-level timestamps everywhere
- Add Sentry or similar for application exceptions
- Add structured logs with `job_id`, `filing_id`, `accession_no`, and `provider`

## 14. AI Quality and Evaluation Strategy

Do not trust first-pass summaries without measurement.

Build an evaluation set of 50 to 100 known 10-Q filings and score:

- sentiment correctness
- theme classification precision and recall
- executive summary usefulness
- evidence quality
- consistency across re-runs

Add automated checks:

- JSON schema validation
- no empty executive summary
- sentiment always one of three labels
- theme keys always from allowed taxonomy
- at least one evidence item per emitted theme

Human review loop:

- Start with analyst review for the first 100 to 200 processed filings
- Track false-positive themes
- Tune prompt and schema versions
- Keep all prompt versions in source control

## 15. Example Code Snippets

### Example 1: sec-api filing search client

```python
import httpx


class SecApiClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.sec-api.io"

    async def search_10q_filings(self, cik: str, start_date: str, end_date: str) -> dict:
        payload = {
            "query": f'cik:{cik} AND formType:"10-Q" AND filedAt:[{start_date} TO {end_date}]',
            "from": "0",
            "size": "50",
            "sort": [{"filedAt": {"order": "desc"}}],
        }
        headers = {"Authorization": self.api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
```

### Example 2: section extraction

```python
import httpx


async def extract_section(api_key: str, filing_url: str, item_code: str) -> str:
    params = {
        "url": filing_url,
        "item": item_code,
        "type": "text",
        "token": api_key,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get("https://api.sec-api.io/extractor", params=params)
        response.raise_for_status()
        return response.text
```

### Example 3: OpenAI structured output

```python
import json
from openai import OpenAI


client = OpenAI()

INSIGHT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "executive_summary": {"type": "string"},
        "investor_pros": {"type": "array", "items": {"type": "string"}},
        "investor_cons": {"type": "array", "items": {"type": "string"}},
        "sentiment": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "sentiment_score": {"type": "number"},
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "theme": {"type": "string"},
                    "direction": {"type": "string"},
                    "strength": {"type": "number"},
                    "summary": {"type": "string"}
                },
                "required": ["theme", "direction", "strength", "summary"]
            }
        },
        "key_risks": {"type": "array", "items": {"type": "string"}},
        "key_opportunities": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"}
    },
    "required": [
        "executive_summary",
        "investor_pros",
        "investor_cons",
        "sentiment",
        "sentiment_score",
        "themes",
        "key_risks",
        "key_opportunities",
        "confidence"
    ]
}

response = client.responses.create(
    model="gpt-5.4-mini",
    reasoning={"effort": "medium"},
    input=[
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": "You are a financial filings analyst. Return only schema-valid output."
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Analyze the following 10-Q sections and produce investor insights..."
                }
            ],
        },
    ],
    text={
        "format": {
            "type": "json_schema",
            "strict": True,
            "name": "filing_insight",
            "schema": INSIGHT_SCHEMA,
        }
    },
)

insight = json.loads(response.output_text)
```

### Example 4: Celery analysis pipeline

```python
from celery import chain


def enqueue_filing_pipeline(filing_id: str) -> None:
    chain(
        discover_sections.s(filing_id),
        summarize_sections.s(),
        synthesize_filing_insight.s(),
        correlate_price_windows.s(),
    ).delay()
```

## 16. Recommended Delivery Plan

### Milestone 1: Foundation

- Initialize Flask API, worker, React app, PostgreSQL, Redis
- Add migrations
- Add `companies`, `filings`, `jobs` tables
- Add environment config and secrets handling

Exit criteria:

- Local stack boots with Docker Compose
- Health endpoints pass
- Database migrations run cleanly

### Milestone 2: Filing ingestion

- Build S&P 500 universe loader
- Build sec-api Query API client
- Store filings with dedupe by `accessionNo`
- Add backfill job and status tracking

Exit criteria:

- Backfill latest 4 quarters for 5 test companies
- No duplicate filings

### Milestone 3: Section extraction

- Build Extractor API client
- Extract `part1item2` and `part2item1a`
- Save raw sections and hashes
- Add retry and failure handling

Exit criteria:

- 95%+ successful extraction for target sample

### Milestone 4: AI insights

- Add OpenAI client
- Add JSON schema validation
- Build section summarization plus filing synthesis
- Store prompt/model/token metadata

Exit criteria:

- Stable schema-valid outputs for 50 sample filings

### Milestone 5: Dashboard

- Build company explorer
- Build filing detail page
- Build compare page
- Build trends page

Exit criteria:

- Users can filter by ticker, date, sentiment, and theme
- Users can compare multiple filings side by side

### Milestone 6: Price correlation

- Add market data provider
- Compute event windows and abnormal returns
- Surface on filing detail and trends pages

Exit criteria:

- T+1, T+5, and T+20 returns available for processed filings

### Milestone 7: Production hardening

- Observability
- Dead-letter queues
- Batch backfills
- Prompt caching
- Evaluation dashboard

Exit criteria:

- Platform handles full S&P 500 quarterly ingestion
- Backfills are resumable
- Failure recovery is operator-friendly

## 17. Final Recommendation

Build Filing Intelligence as a worker-first data platform:

- Flask API for serving and orchestration
- PostgreSQL as the system of record
- Redis + Celery for asynchronous ingestion and analysis
- sec-api Query + Stream + Extractor APIs for filing discovery and section extraction
- OpenAI Responses API with Structured Outputs for reliable investor insight generation
- React + Tailwind for a fast comparison-oriented research UI

This design is scalable enough for the full S&P 500, cost-conscious for backfills, and explainable enough for investor-facing workflows because every theme and sentiment output can be tied back to evidence from the filing text.

## 18. Reference Links

- OpenAI models overview: https://developers.openai.com/api/docs/models
- OpenAI Responses API: https://developers.openai.com/api/reference/resources/responses/methods/create
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Background mode: https://developers.openai.com/api/docs/guides/background
- OpenAI Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- OpenAI Batch API: https://developers.openai.com/api/docs/guides/batch
- sec-api Query API: https://sec-api.io/docs/query-api/
- sec-api Extractor API: https://sec-api.io/docs/sec-filings-item-extraction-api
- sec-api Stream API: https://sec-api.io/docs/stream-api
- sec-api Mapping API: https://sec-api.io/docs/mapping-api
- Polygon stocks overview: https://polygon.io/docs/rest/stocks/overview/
- Alpha Vantage documentation: https://www.alphavantage.co/documentation/
- Alpha Vantage support and usage limits: https://www.alphavantage.co/support/
