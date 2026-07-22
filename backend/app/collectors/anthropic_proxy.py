"""Anthropic (Claude / Claude Code) forward-proxy collector.

Captures per-request token usage by intercepting Claude Code's OWN traffic to
``api.anthropic.com``. Unlike the admin-usage poller, this works with a
**subscription** (Claude Pro/Max OAuth) too, because token counts are read
directly from the streamed ``/v1/messages`` response — no admin key required.

Wire Claude Code to it by setting::

    ANTHROPIC_BASE_URL=http://localhost:<anthropic_proxy_port>

and keep its normal login (OAuth or API key). Every Messages request is then
forwarded to Anthropic and its usage (input / output / cache tokens) is parsed
out of the response and ingested into ``enriched_request`` with
``provider=anthropic``, ``source=anthropic_proxy``.
"""
import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse

from app.collectors.base import BaseCollector
from app.collectors.proxy import _HOP_BY_HOP, _filter_response_headers
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER = "anthropic"
_SOURCE = "anthropic_proxy"

# Forward everything, but only meter real Messages calls (not count_tokens).
_CAPTURE_MARKER = "v1/messages"
_SKIP_MARKER = "count_tokens"


class _AnthropicUsageAccumulator:
    """Incrementally parse a streamed Anthropic Messages response.

    ``input_tokens`` / cache tokens arrive in the ``message_start`` event (early
    in the stream); ``output_tokens`` arrives in ``message_delta`` (near the
    end). A tail-only window would miss the head, so we scan the whole stream.
    A line buffer makes parsing robust to events split across chunks. Only the
    two events we need are JSON-decoded (cheap substring gate first).
    """

    def __init__(self) -> None:
        self.input_tokens = 0
        self.cache_creation = 0
        self.cache_read = 0
        self.output_tokens = 0
        self.model: Optional[str] = None
        self._buffer = ""

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk.decode("utf-8", errors="ignore")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        line = line.strip()
        if not line.startswith("data:"):
            return
        payload = line[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            return
        # Cheap pre-filter: only the two events we care about carry usage.
        if '"message_start"' not in payload and '"message_delta"' not in payload:
            return
        try:
            obj = json.loads(payload)
        except (ValueError, TypeError):
            return
        if not isinstance(obj, dict):
            return
        etype = obj.get("type")
        if etype == "message_start":
            msg = obj.get("message") or {}
            usage = msg.get("usage") or {}
            self.input_tokens = int(usage.get("input_tokens") or 0)
            self.cache_creation = int(usage.get("cache_creation_input_tokens") or 0)
            self.cache_read = int(usage.get("cache_read_input_tokens") or 0)
            model = msg.get("model")
            if isinstance(model, str):
                self.model = model
        elif etype == "message_delta":
            usage = obj.get("usage") or {}
            if usage.get("output_tokens") is not None:
                self.output_tokens = int(usage["output_tokens"])

    def result(self, fallback_model: Optional[str] = None) -> dict:
        prompt = self.input_tokens + self.cache_creation + self.cache_read
        completion = self.output_tokens
        return {
            "model": self.model or fallback_model,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "metadata": {
                "input_tokens": self.input_tokens,
                "cache_creation_input_tokens": self.cache_creation,
                "cache_read_input_tokens": self.cache_read,
                "output_tokens": self.output_tokens,
            },
        }


def _extract_nonstream_usage(body: Any, fallback_model: Optional[str]) -> dict:
    if not isinstance(body, dict):
        return {
            "model": fallback_model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }
    usage = body.get("usage") or {}
    inp = int(usage.get("input_tokens") or 0)
    cache_create = int(usage.get("cache_creation_input_tokens") or 0)
    cache_read = int(usage.get("cache_read_input_tokens") or 0)
    out = int(usage.get("output_tokens") or 0)
    model = body.get("model") or fallback_model
    prompt = inp + cache_create + cache_read
    return {
        "model": model,
        "prompt_tokens": prompt,
        "completion_tokens": out,
        "total_tokens": prompt + out,
        "metadata": {
            "input_tokens": inp,
            "cache_creation_input_tokens": cache_create,
            "cache_read_input_tokens": cache_read,
            "output_tokens": out,
        },
    }


def _is_streaming(body: bytes) -> bool:
    if not body:
        return False
    try:
        return bool(json.loads(body).get("stream"))
    except (ValueError, TypeError):
        return False


def _extract_model(body: bytes) -> Optional[str]:
    if not body:
        return None
    try:
        obj = json.loads(body)
    except (ValueError, TypeError):
        return None
    if isinstance(obj, dict):
        model = obj.get("model")
        if isinstance(model, str):
            return model
    return None


def _should_capture(full_path: str) -> bool:
    return _CAPTURE_MARKER in full_path and _SKIP_MARKER not in full_path


def _build_anthropic_proxy_app(
    target_url: str,
    *,
    transport: Optional[httpx.BaseTransport] = None,
    ingest: Optional[Callable[[dict], Any]] = None,
) -> FastAPI:
    """Build the Anthropic forward-proxy FastAPI app.

    ``transport`` and ``ingest`` are test seams: in production neither is set
    (real upstream client + DB-writing ingest). In tests, a MockTransport and a
    capturing callback exercise the full forward+parse+capture path offline.
    """
    base = target_url.rstrip("/")
    app = FastAPI(title="Anthropic Usage Proxy", docs_url=None, redoc_url=None, openapi_url=None)

    client_kwargs: dict[str, Any] = {
        "timeout": httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0),
        "follow_redirects": False,
    }
    if transport is not None:
        client_kwargs["transport"] = transport
    client = httpx.AsyncClient(**client_kwargs)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await client.aclose()

    async def _do_ingest(captured: dict, latency_ms: float, status_code: int, is_streaming: bool) -> None:
        if captured.get("total_tokens", 0) <= 0:
            return
        record = {
            "provider": _PROVIDER,
            "source": _SOURCE,
            "model": captured.get("model") or "unknown",
            "prompt_tokens": captured.get("prompt_tokens", 0),
            "completion_tokens": captured.get("completion_tokens", 0),
            "total_tokens": captured.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "status_code": status_code,
            "application": settings.anthropic_proxy_application,
            "user_id": settings.user_identity,
            "is_streaming": is_streaming,
            "metadata": captured.get("metadata", {}),
        }
        if ingest is not None:
            res = ingest(record)
            if asyncio.iscoroutine(res):
                await res
            return
        # Default: write to the monitor database.
        from app.dependencies import async_session_maker
        from app.services.reconciliation_service import ReconciliationService

        async with async_session_maker() as session:
            await ReconciliationService(session).ingest_request(record)

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    )
    async def proxy(full_path: str, request: Request):
        target = f"{base}/{full_path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        incoming = dict(request.headers)
        # Strip hop-by-hop (incl. host) and forward whatever auth Claude Code
        # sent (x-api-key OR OAuth bearer). Never inject our own credentials.
        fwd_headers = {k: v for k, v in incoming.items() if k.lower() not in _HOP_BY_HOP}

        body = await request.body()
        streaming = _is_streaming(body)
        capture = _should_capture(full_path)
        fallback_model = _extract_model(body)
        method = request.method
        started = time.perf_counter()

        if streaming:
            request_obj = client.build_request(method, target, headers=fwd_headers, content=body)
            try:
                upstream = await client.send(request_obj, stream=True)
            except httpx.HTTPError as exc:
                logger.warning("Anthropic proxy streaming upstream error: %s", exc)
                return Response(content=f"Upstream error: {exc}", status_code=502)

            resp_headers = _filter_response_headers(upstream.headers)
            media_type = upstream.headers.get("content-type", "text/event-stream")
            status_code = upstream.status_code
            accumulator = _AnthropicUsageAccumulator()

            async def body_iter():
                try:
                    async for chunk in upstream.aiter_bytes():
                        yield chunk
                        if capture:
                            accumulator.feed(chunk)
                finally:
                    await upstream.aclose()

                if not capture:
                    return

                latency_ms = (time.perf_counter() - started) * 1000.0
                captured = accumulator.result(fallback_model)
                try:
                    await _do_ingest(captured, latency_ms, status_code, True)
                except Exception as exc:  # noqa: BLE001 - never break the stream on ingest failure
                    logger.exception("Anthropic proxy ingest (stream) failed: %s", exc)

            return StreamingResponse(
                body_iter(),
                status_code=status_code,
                headers=resp_headers,
                media_type=media_type,
            )

        # Non-streaming: forward, then read usage from the JSON body.
        try:
            upstream = await client.request(method, target, headers=fwd_headers, content=body)
        except httpx.HTTPError as exc:
            logger.warning("Anthropic proxy upstream error for %s: %s", full_path, exc)
            return Response(content=f"Upstream error: {exc}", status_code=502)

        latency_ms = (time.perf_counter() - started) * 1000.0
        captured: dict = {
            "model": fallback_model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }
        if capture:
            try:
                captured = _extract_nonstream_usage(upstream.json(), fallback_model)
            except (ValueError, TypeError):
                pass
            try:
                await _do_ingest(captured, latency_ms, upstream.status_code, False)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Anthropic proxy ingest failed: %s", exc)

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=_filter_response_headers(upstream.headers),
            media_type=upstream.headers.get("content-type"),
        )

    return app


class AnthropicProxyCollector(BaseCollector):
    def __init__(self):
        super().__init__("anthropic_proxy")
        self.is_healthy = True
        self._server: Optional[uvicorn.Server] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if not settings.anthropic_proxy_enabled:
            logger.info("AnthropicProxyCollector is disabled in settings.")
            return

        self.is_running = True
        app = _build_anthropic_proxy_app(settings.anthropic_proxy_target_url)
        config = uvicorn.Config(
            app,
            host=settings.host,
            port=settings.anthropic_proxy_port,
            log_level=settings.log_level.lower(),
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve(), name="anthropic-proxy-server")
        logger.info(
            "AnthropicProxyCollector started on port %s -> %s",
            settings.anthropic_proxy_port,
            settings.anthropic_proxy_target_url,
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        self._server = None
        self._task = None
        self.is_running = False
        logger.info("AnthropicProxyCollector stopped.")

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.is_healthy,
            "enabled": settings.anthropic_proxy_enabled,
            "port": settings.anthropic_proxy_port if self.is_running else None,
            "target": settings.anthropic_proxy_target_url,
        }
