# GLM Usage Monitor

Account-wide **Z.ai GLM-5.2 usage monitoring**. Polls the official Z.ai quota
endpoint, ingests per-request telemetry via webhook, and serves a live React
dashboard with both **total account usage** and **per-user ("my") usage**.

## Architecture

```
┌──────────────────┐    webhook     ┌─────────────────────────┐
│  Your AI tools   │ ─────────────▶ │  FastAPI backend        │
│  (opencode, CLI, │                │  - collectors (official │
│  IDE plugins...) │                │    + proxy + log +      │
└──────────────────┘                │    webhook)             │
                                     │  - reconciliation svc   │
┌──────────────────┐                │  - analytics svc        │
│  Z.ai API        │ ◀── poll ───── │  - APScheduler jobs     │
└──────────────────┘                │  - SQLite (async)       │
                                     │  - REST + WebSocket     │
                                     └────────┬────────────────┘
                                              │
                                     ┌────────▼────────┐
                                     │  React + Vite   │
                                     │  dashboard      │
                                     └─────────────────┘
```

### Backend (`backend/`)
- **`app/main.py`** — FastAPI app + lifespan that creates DB tables, starts all
  collectors, and registers the APScheduler quota-poll job.
- **`app/collectors/`** — `OfficialCollector` (polls Z.ai), `WebhookCollector`,
  `ProxyCollector`, `LogCollector`, orchestrated by `CollectorManager`.
- **`app/services/`**
  - `QuotaService` — fetches & stores quota snapshots, broadcasts WS updates.
  - `ReconciliationService` — dedupes + ingests per-request telemetry.
  - `AnalyticsService` — real queries for summary, trends, breakdowns,
    burn-rate, unattributed usage, **me-vs-total**.
- **`app/api/`** — REST routes (`/quota`, `/analytics`, `/requests`,
  `/collectors`, `/webhook`, `/health`) and a WebSocket (`/ws`).
- **`app/jobs/`** — APScheduler glue (quota poll, aggregation, reconciliation).

### Frontend (`frontend/`)
React 19 + Vite + Tailwind + Recharts. Live dashboard with quota gauges,
burn-rate, usage trends, model/tool/user breakdowns, a heatmap, and a request
explorer with CSV/JSON export.

## Quick start (local dev, Windows PowerShell)

1. **Configure environment**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env and set GLM_MONITOR_ZAI_API_KEY and GLM_MONITOR_USER_IDENTITY
   ```

2. **Backend**
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   uvicorn app.main:app --reload --port 8000
   ```
   Tables are created automatically on first boot via `Base.metadata.create_all`.

3. **Frontend** (new terminal)
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
   Dashboard opens on http://localhost:5173.

Or use the helper scripts at the repo root: `.\dev.ps1` (or `dev.cmd`).

## REST API cheat-sheet (prefix `/api/v1`)

| Method | Path                     | Description                                           |
|--------|--------------------------|-------------------------------------------------------|
| GET    | `/health`                | Liveness probe                                        |
| GET    | `/quota/current`         | Latest cached quota snapshot                          |
| GET    | `/analytics/summary`     | Totals for `?period=daily\|hourly\|weekly\|monthly`  |
| GET    | `/analytics/trends`      | `?days=7` daily token/request series                  |
| GET    | `/analytics/by-model`    | Token totals grouped by model                         |
| GET    | `/analytics/by-application` | Token totals grouped by application                |
| GET    | `/analytics/by-user`     | Token totals grouped by `user_id`                     |
| GET    | `/analytics/me`          | Summary for `GLM_MONITOR_USER_IDENTITY`               |
| GET    | `/analytics/me-vs-total` | Side-by-side per-day totals, me vs. everyone          |
| GET    | `/analytics/heatmap`     | `?days=84` daily token intensity for heatmap          |
| GET    | `/analytics/burn-rate`   | Tokens/hr from last hour + exhaustion estimate        |
| GET    | `/analytics/unattributed`| Official % vs. enriched % gap                         |
| GET    | `/requests/`             | Filterable list (`source,model,application,user_id`)  |
| GET    | `/requests/export`       | `?format=csv|json`                                    |
| GET    | `/collectors/status`     | Per-collector health                                  |
| POST   | `/collectors/{type}/toggle?enable=true`                 |
| POST   | `/webhook/ingest`        | Push a per-request payload (see `WebhookPayload`)     |
| WS     | `/ws`                    | Live `quota_update` / `new_request` events            |

### Webhook payload
```json
{
  "request_id": "optional-dedup-id",
  "model": "glm-5.2",
  "prompt_tokens": 1200,
  "completion_tokens": 350,
  "total_tokens": 1550,
  "application": "opencode",
  "user_id": "me@example.com",
  "latency_ms": 820.5,
  "status_code": 200,
  "is_streaming": false,
  "metadata": {}
}
```
If `GLM_MONITOR_WEBHOOK_SECRET` is set, send it as `X-Webhook-Secret`.

## Per-user attribution

Tools must include `user_id` in the webhook payload. Set
`GLM_MONITOR_USER_IDENTITY` to your own `user_id` to enable the **Me vs Total**
comparison view; usage that doesn't carry `user_id` is still counted toward
totals and shows up as "unattributed" in the per-user breakdown.

## Docker

```bash
make up          # backend + frontend
make up-proxy    # also start the proxy collector
make down
make test        # backend pytest
```

## Tests
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```

## Project status / known gaps
- Proxy & log collectors are scaffolds (no HTTP server / file watcher impl yet)
  - the webhook path is fully functional and is the recommended way to feed
  per-request data today.
- Alembic is wired up but the dev path uses `create_all`; add real migrations
  before relying on schema changes in production.
