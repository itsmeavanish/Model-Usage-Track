# AGENTS.md

Quick memory for this repo.

## What it is
Monitors Z.ai GLM usage **plus OpenAI (GPT/ChatGPT) and Anthropic (Claude/Claude Code) usage**. Backend = FastAPI + SQLite (port 8000). Frontend = React + Vite (port 5173). Run both: `./dev.ps1`.

## The #1 thing to know
**All analytics panels read from the `enriched_request` table.** If it's empty, the dashboard shows nothing (only `AccountOverview` works — it uses `quota_snapshot`; the Z.ai provider poller also feeds `quota_snapshot`). When "no data shows", check `SELECT COUNT(*) FROM enriched_request` first. Each row has a `provider` column (`zai` / `openai` / `anthropic`); legacy rows are NULL and bucketed as `zai`.

## Data flow
- **Official collector** polls Z.ai quota every 60s → `quota_snapshot` table.
- **Provider admin pollers** (OpenAI/Anthropic) poll each platform's admin usage API (grouped by model, hourly buckets) every ~5min → `enriched_request` with `source`=`openai_admin`/`anthropic_admin`, `provider`=`openai`/`anthropic`. Re-polling upserts by deterministic `{provider}:{model}:{bucket}` id so partial buckets fill in without double-counting.
- **Request-level data** enters `enriched_request` via collectors: proxy / webhook / log (provider tag defaults to `zai`).
- `useLiveData` hook (frontend) re-fetches on a 30s tick or WebSocket signal.

## Collectors (`backend/app/collectors/`)
- `official.py` — quota poller (httpx). Works.
- `proxy.py` — **REAL forward proxy** on port 8080 → `https://api.z.ai`. Forwards all requests, captures `usage` from chat/completions (streaming + non-streaming), ingests with `source=proxy`. Started by `ProxyCollector.start()` which runs a nested `uvicorn.Server`.
- `webhook.py` — passive; data arrives via `POST /api/v1/webhook/ingest`.
- `log_parser.py` — stub.
- `openai.py` — polls `GET /v1/organization/usage/completions` (Admin API, `sk-admin-` key, `group_by[]=model`, hourly buckets, paginate via `has_more`/`next_page`). Normalizes each (model, bucket) → `ingest_aggregate_usage` with `provider=openai`, `source=openai_admin`.
- `anthropic.py` — polls `GET /v1/organizations/usage_report/messages` (Admin API, `sk-ant-admin01-` key via `x-api-key`, `anthropic-version: 2023-06-01`, `bucket_width=1h&group_by[]=model`). Input = `uncached + cache_read + cache_creation(5m+1h)`. Ingests with `provider=anthropic`, `source=anthropic_admin`.
- `anthropic_proxy.py` — **forward proxy** on port 8090 → `https://api.anthropic.com`. Captures per-request usage from Claude Code's own `/v1/messages` traffic (streaming SSE + non-streaming). **Works on Claude Pro/Max subscription (OAuth) too**, unlike the admin poller. Ingests with `provider=anthropic`, `source=anthropic_proxy`. Enable via `ANTHROPIC_PROXY_ENABLED=true`; point Claude Code with `ANTHROPIC_BASE_URL=http://localhost:8090`. `_AnthropicUsageAccumulator` scans the whole stream (input/cache tokens are in `message_start` at the head; output in `message_delta` at the tail) — a tail-only window would miss them.

Both provider pollers are driven by APScheduler jobs (`jobs/provider_poll.py`) wired in `main.py`; only scheduled when `*_ENABLED=true`. They re-query a trailing ~3h window each poll so partial hourly buckets settle via upsert.

To capture real usage, point tools at the proxy: `base_url = http://localhost:8080/api/paas/v4` (instead of `https://api.z.ai/api/paas/v4`).

## Gotchas learned
- **The GLM Coding Plan is NOT capturable.** opencode's `zai-coding-plan/glm-5.2` routes through opencode's own gateway, not Z.ai's public API. The coding-plan key (`7afbec...`) returns **429 "Insufficient balance" (code 1113)** for `glm-5.2`/`glm-4.6` on the plain `api.z.ai/api/paas/v4` endpoint, so the monitor's proxy cannot intercept coding-plan traffic. Only the Z.ai **quota %** (polled by the official collector) is visible. To get per-request token tracking you must use a **separate prepaid Z.ai API key** routed through the proxy (see `opencode.jsonc` provider `zai-tracked`). `glm-4.5-flash` works on prepaid today; `glm-5.2` needs balance.
- **Subscription usage isn't trackable by any API.** ChatGPT Plus/Pro (OAuth), Claude Pro/Max, and the GLM Coding Plan are all closed subscriptions. The OpenAI/Anthropic admin pollers only see pay-as-you-go API billing (`sk-admin-` / `sk-ant-admin01-` keys). **Exception:** Claude Code (even on a Claude subscription) **is** trackable via the `anthropic_proxy` collector — it intercepts Claude Code's own traffic and reads usage from the streamed response (see `collectors/anthropic_proxy.py`).
- **uvicorn `--reload` only watches `.py` files, NOT `.env`.** After editing `.env`, manually restart the backend.
- **httpx auto-decompresses** response bodies — strip `content-encoding` + `content-length` from forwarded response headers (see `_filter_response_headers`).
- **SSE usage parsing must be line-by-line** — a greedy regex with `re.DOTALL` spans events and fails. Usage is in the LAST `data:` chunk.
- **Tests must disable the proxy**: `conftest.py` sets `GLM_MONITOR_PROXY_ENABLED=false` so the TestClient doesn't spawn a real server.
- **`useLiveData` preserves previous data on refetch error** (don't null it out — that blanks the UI on refresh).
- Z.ai API key in `.env` works for the monitor endpoint but `glm-4.6` returns "insufficient balance" for direct chat calls; `glm-4.5-flash` works for testing.

## Commands
```powershell
# Backend
cd backend; .\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
.\venv\Scripts\python.exe -m pytest          # 16 tests
.\venv\Scripts\python.exe -m ruff check app

# Frontend
cd frontend; npm run dev
npx tsc -b --noEmit; npx oxlint

# Health checks
curl http://localhost:8000/api/v1/collectors/status
curl http://localhost:8000/api/v1/analytics/by-application
```

## Config (`.env`, prefix `GLM_MONITOR_`)
Key flags: `PROXY_ENABLED`, `WEBHOOK_ENABLED`, `OPENAI_ENABLED`/`OPENAI_API_KEY` (Admin `sk-admin-`), `ANTHROPIC_ENABLED`/`ANTHROPIC_API_KEY` (Admin `sk-ant-admin01-`), `USER_IDENTITY` (your email, for Me-vs-Total), `PROXY_PORT` (8080), `PROXY_TARGET_URL`. Pydantic-settings reads `backend/.env` and `../.env` (repo root).

## Identity
`GLM_MONITOR_USER_IDENTITY=avanishupadhyay633@gmail.com`. Captured rows get `user_id` from `X-User-Id` header or this fallback; `application` from `X-Application` header, `USER_APPLICATION`, or `"proxy"`.
