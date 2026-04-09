# sec-filing-analyzer

Production-ready starter backend for a Filing Intelligence platform that:

- tracks S&P 500 companies
- fetches SEC 10-Q filings through `sec-api.io`
- extracts MD&A and Risk Factors sections
- analyzes filing text with the OpenAI Responses API
- stores filings, sections, and AI output in PostgreSQL
- processes long-running work with Celery and Redis

## Prerequisites

- Docker
- Docker Compose
- sec-api.io API key
- OpenAI API key

## Quick Start

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Fill in `OPENAI_API_KEY` and `SEC_API_KEY` in `.env`.
   If you are using Gemini instead, set `AI_PROVIDER=gemini`, add `GEMINI_API_KEY`, and set a real `SEC_USER_AGENT` with your contact email.

3. Start the stack:

```bash
docker compose up
```

4. Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

5. Open the dashboard:

```bash
http://localhost:8000/
```

## Discover Filings

Create a company if needed, search for 10-Q filings, and store them:

```bash
curl -X POST http://localhost:8000/filings/discover \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "cik": "0000320193",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }'
```

## End-to-End Flow

1. `POST /filings/discover`
2. `POST /filings/<filing_id>/analyze`
3. `GET /filings/<filing_id>`

The Celery task:

1. loads the filing from PostgreSQL
2. extracts `part1item2` and `part2item1a` from sec-api.io
3. stores the sections in `filing_sections`
4. sends the combined filing context to OpenAI `gpt-5.4-mini`
5. stores the structured AI output in `ai_runs`
