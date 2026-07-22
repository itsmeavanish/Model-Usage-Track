# GLM Usage Monitor

Account-wide usage monitoring for **Z.ai (GLM)**, **OpenAI (GPT/ChatGPT)**, and
**Anthropic (Claude)**. Polls the official Z.ai quota endpoint, captures
per-request telemetry via a forward proxy or webhook, polls OpenAI/Anthropic
admin usage APIs, and serves a live React dashboard with both **total account
usage** and **per-user ("my") usage**.

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
- **`app/collectors/`** — `OfficialCollector` (polls Z.ai quota), `ProxyCollector`
  (forward proxy → captures GLM usage), `WebhookCollector`, `LogCollector`,
  `OpenAICollector` + `AnthropicCollector` (poll admin usage APIs), orchestrated
  by `CollectorManager`.
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

## How to track your usage

The dashboard only shows traffic the monitor can **see**. Token tracking works
for traffic routed through the **proxy** (or pushed via webhook); OpenAI and
Anthropic also support admin-API polling. Each captured row is tagged with a
`provider` (`zai` / `openai` / `anthropic`) — see the **Usage by Provider** card
and `/api/v1/analytics/by-provider`.

> **Subscriptions are not trackable by any API.** The GLM Coding Plan, ChatGPT
> Plus/Pro, and Claude Pro/Max are closed subscriptions. Only **pay-as-you-go
> API keys** can be metered.

### 1. Z.ai (GLM) — route a prepaid key through the proxy
> The **GLM Coding Plan** (e.g. opencode's `zai-coding-plan/glm-5.2`) routes
> through opencode's gateway, not Z.ai's public API, so it **cannot** be
> captured. Use a separate **prepaid** Z.ai API key for per-request tracking.

1. Create a prepaid key (+ balance) at <https://z.ai/manage-apikey/apikey-list>.
2. In `.env`, keep `GLM_MONITOR_PROXY_ENABLED=true` (proxy on `:8080` → `https://api.z.ai`).
3. Point your GLM client at the proxy instead of Z.ai:
   - base URL: `http://localhost:8080/api/paas/v4`
   - header: `Authorization: Bearer <your prepaid Z.ai key>`
4. Send a request — it shows up in the dashboard within seconds.

**opencode example** — add a tracked provider to `opencode.jsonc`:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "zai-tracked/glm-4.5-flash",
  "provider": {
    "zai-tracked": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Z.ai via monitor proxy (tracked)",
      "options": { "baseURL": "http://localhost:8080/api/paas/v4" },
      "models": { "glm-4.5-flash": {}, "glm-5.2": {} }
    }
  }
}
```
Store the prepaid key under the `zai-tracked` credential — via `/connect` →
Other, or directly in `~/.local/share/opencode/auth.json`:
```json
"zai-tracked": { "type": "api", "key": "<your prepaid Z.ai key>" }
```
The monitor backend + proxy **must stay running** while you use this provider.

### 2. OpenAI (GPT) and Anthropic (Claude) — admin usage polling
These platforms expose org-wide **Admin usage APIs** (hourly, grouped by model).
The monitor polls them on a schedule — no proxy needed.

In `.env`:
```
GLM_MONITOR_OPENAI_ENABLED=true
GLM_MONITOR_OPENAI_API_KEY=sk-admin-...            # platform.openai.com → Admin keys
GLM_MONITOR_ANTHROPIC_ENABLED=true
GLM_MONITOR_ANTHROPIC_API_KEY=sk-ant-admin01-...   # console.anthropic.com → Admin API key
```
Restart the backend (uvicorn `--reload` does **not** watch `.env`). Claude Code
is tracked only when run against your Anthropic API key, not a Claude subscription.

### 2b. Claude Code via the Anthropic proxy (works on subscription too)
If you use **Claude Code on a Claude Pro/Max subscription**, the admin API above
won't see it — but the monitor's **Anthropic forward proxy** will. It intercepts
Claude Code's own traffic to `api.anthropic.com` and reads token usage from the
streamed `Messages` response, so it works with OAuth subscription **or** an API key.

In `.env`:
```
GLM_MONITOR_ANTHROPIC_PROXY_ENABLED=true
GLM_MONITOR_ANTHROPIC_PROXY_PORT=8090
```
Restart the backend, then point Claude Code at the proxy:
```
# PowerShell (current session)
$env:ANTHROPIC_BASE_URL = "http://localhost:8090"
claude ...
```
Captured rows are tagged `provider=anthropic`, `source=anthropic_proxy`,
`application=claude-code`. The monitor must stay running while you use Claude Code.

### 3. Webhook (any provider)
Push a per-request payload to `POST /api/v1/webhook/ingest` (see payload below).
Optional `provider` field defaults to `zai`.

## REST API cheat-sheet (prefix `/api/v1`)

| Method | Path                     | Description                                           |
|--------|--------------------------|-------------------------------------------------------|
| GET    | `/health`                | Liveness probe                                        |
| GET    | `/quota/current`         | Latest cached quota snapshot                          |
| GET    | `/analytics/summary`     | Totals for `?period=daily\|hourly\|weekly\|monthly`  |
| GET    | `/analytics/trends`      | `?days=7` daily token/request series                  |
| GET    | `/analytics/by-model`    | Token totals grouped by model                         |
| GET    | `/analytics/by-application` | Token totals grouped by application                |
| GET    | `/analytics/by-provider` | Token totals grouped by provider (`zai`\|`openai`\|`anthropic`) |
| GET    | `/analytics/by-user`     | Token totals grouped by `user_id`                     |
| GET    | `/analytics/me`          | Summary for `GLM_MONITOR_USER_IDENTITY`               |
| GET    | `/analytics/me-vs-total` | Side-by-side per-day totals, me vs. everyone          |
| GET    | `/analytics/heatmap`     | `?days=84` daily token intensity for heatmap          |
| GET    | `/analytics/burn-rate`   | Tokens/hr from last hour + exhaustion estimate        |
| GET    | `/analytics/unattributed`| Official % vs. enriched % gap                         |
| GET    | `/requests/`             | Filterable list (`source,model,application,user_id,provider`) |
| GET    | `/requests/export`       | `?format=csv|json`                                    |
| GET    | `/collectors/status`     | Per-collector health                                  |
| POST   | `/collectors/{type}/toggle?enable=true`                 |
| POST   | `/webhook/ingest`        | Push a per-request payload (see `WebhookPayload`)     |
| WS     | `/ws`                    | Live `quota_update` / `new_request` events            |

### Webhook payload
```json
{
  "request_id": "optional-dedup-id",
  "provider": "zai",
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
- Proxy collector is fully implemented (real forward proxy on port 8080 that
  captures streaming + non-streaming usage). Webhook is also fully functional.
  Log collector is still a stub.
- OpenAI + Anthropic admin-usage pollers are implemented and gated behind
  `*_ENABLED` flags + admin keys (see "How to track your usage").
- **The GLM Coding Plan is not capturable** — use a prepaid key via the proxy.
- Alembic is wired up but the dev path uses `create_all` (plus a small additive
  migration helper for new columns); add real migrations before relying on
  schema changes in production.
