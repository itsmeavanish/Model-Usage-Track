import asyncio
import json
import logging
import time
from typing import Any, Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# Hop-by-hop headers (RFC 7230) that must not be forwarded verbatim.
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

# Request path fragments that identify completion endpoints worth metering.
_CAPTURE_PATH_MARKERS = ("chat/completions", "/completions")

# Size of the trailing byte window kept from an SSE stream to extract the
# final usage chunk (usage is emitted in the last data frame).
_SSE_TAIL_BYTES = 8192


def _is_streaming_request(body: bytes) -> bool:
    if not body:
        return False
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return False
    return bool(isinstance(payload, dict) and payload.get("stream"))


def _extract_request_model(body: bytes) -> Optional[str]:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return None
    if isinstance(payload, dict):
        model = payload.get("model")
        if isinstance(model, str):
            return model
    return None


def _parse_usage(usage: Any) -> tuple[int, int, int]:
    if not isinstance(usage, dict):
        return 0, 0, 0
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    return prompt, completion, total


def _extract_usage_from_sse(tail: bytes) -> tuple[Optional[dict], Optional[str]]:
    """Scan the trailing bytes of an SSE stream for the final usage frame.

    Each SSE event is a single ``data: {json}`` line, so parse per line rather
    than with a multi-line regex (which would greedily span events and fail).
    """
    text = tail.decode("utf-8", errors="ignore")
    usage: Optional[dict] = None
    model: Optional[str] = None
    for line in text.splitlines():
        payload = line.strip()
        if not payload.startswith("data:"):
            continue
        payload = payload[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except (ValueError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("usage"):
            usage = obj["usage"]
        if obj.get("model"):
            model = obj["model"]
    return usage, model


def _filter_response_headers(headers: httpx.Headers) -> dict[str, str]:
    # httpx auto-decompresses the body, so drop content-encoding/length to avoid
    # sending the client a decoded body with a stale "gzip" label.
    skip = _HOP_BY_HOP | {"content-encoding", "content-length"}
    return {k: v for k, v in headers.items() if k.lower() not in skip}


def _build_proxy_app(target_url: str) -> FastAPI:
    base = target_url.rstrip("/")
    app = FastAPI(title="GLM Usage Proxy", docs_url=None, redoc_url=None, openapi_url=None)
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=10.0),
        follow_redirects=False,
    )

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await client.aclose()

    async def _ingest(
        *,
        prompt: int,
        completion: int,
        total: int,
        model: Optional[str],
        application: Optional[str],
        user_id: Optional[str],
        latency_ms: float,
        status_code: int,
        is_streaming: bool,
    ) -> None:
        if total <= 0:
            return
        # Deferred import to avoid a circular dependency with app.dependencies.
        from app.dependencies import async_session_maker
        from app.services.reconciliation_service import ReconciliationService

        async with async_session_maker() as session:
            service = ReconciliationService(session)
            await service.ingest_request(
                {
                    "source": "proxy",
                    "model": model or "unknown",
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                    "total_tokens": total,
                    "latency_ms": latency_ms,
                    "status_code": status_code,
                    "application": application,
                    "user_id": user_id,
                    "is_streaming": is_streaming,
                }
            )

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    )
    async def proxy(full_path: str, request: Request):
        target = f"{base}/{full_path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        incoming = dict(request.headers)
        fwd_headers = {k: v for k, v in incoming.items() if k.lower() not in _HOP_BY_HOP}
        if not any(k.lower() == "authorization" for k in fwd_headers):
            fwd_headers["Authorization"] = f"Bearer {settings.zai_api_key.get_secret_value()}"

        body = await request.body()
        is_streaming = _is_streaming_request(body)
        should_capture = any(marker in full_path for marker in _CAPTURE_PATH_MARKERS)
        application = fwd_headers.get("x-application") or settings.user_application or "proxy"
        user_id = fwd_headers.get("x-user-id") or settings.user_identity
        request_model = _extract_request_model(body)

        method = request.method
        started = time.perf_counter()

        if is_streaming:
            return await _stream_response(
                client=client,
                method=method,
                target=target,
                headers=fwd_headers,
                content=body,
                should_capture=should_capture,
                application=application,
                user_id=user_id,
                fallback_model=request_model,
                started=started,
                ingest=_ingest,
            )

        # Non-streaming: forward and capture usage from the JSON body.
        try:
            upstream = await client.request(method, target, headers=fwd_headers, content=body)
        except httpx.HTTPError as exc:
            logger.warning("Proxy upstream error for %s: %s", full_path, exc)
            return Response(content=f"Upstream error: {exc}", status_code=502)

        latency_ms = (time.perf_counter() - started) * 1000.0
        model = request_model
        usage: Optional[dict] = None
        try:
            parsed = upstream.json()
            if isinstance(parsed, dict):
                usage = parsed.get("usage")
                if parsed.get("model"):
                    model = parsed["model"]
        except (ValueError, TypeError):
            pass

        if should_capture and usage:
            prompt, completion, total = _parse_usage(usage)
            try:
                await _ingest(
                    prompt=prompt,
                    completion=completion,
                    total=total,
                    model=model,
                    application=application,
                    user_id=user_id,
                    latency_ms=latency_ms,
                    status_code=upstream.status_code,
                    is_streaming=False,
                )
            except Exception as exc:  # noqa: BLE001 - never break the proxy on ingest failure
                logger.exception("Proxy ingest failed: %s", exc)

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=_filter_response_headers(upstream.headers),
            media_type=upstream.headers.get("content-type"),
        )

    return app


async def _stream_response(
    *,
    client: httpx.AsyncClient,
    method: str,
    target: str,
    headers: dict[str, str],
    content: bytes,
    should_capture: bool,
    application: Optional[str],
    user_id: Optional[str],
    fallback_model: Optional[str],
    started: float,
    ingest,
):
    try:
        upstream = client.stream(method, target, headers=headers, content=content)
        req = await upstream.__aenter__()
    except httpx.HTTPError as exc:
        logger.warning("Proxy streaming upstream error for %s: %s", target, exc)
        return Response(content=f"Upstream error: {exc}", status_code=502)

    resp_headers = _filter_response_headers(req.headers)
    media_type = req.headers.get("content-type", "text/event-stream")
    status_code = req.status_code

    async def body_iter():
        tail = b""
        try:
            async for chunk in req.aiter_bytes():
                yield chunk
                if should_capture:
                    tail = (tail + chunk)[-_SSE_TAIL_BYTES:]
        finally:
            await req.aclose()

        if not should_capture:
            return

        latency_ms = (time.perf_counter() - started) * 1000.0
        usage, model = _extract_usage_from_sse(tail)
        prompt, completion, total = _parse_usage(usage)
        if total > 0:
            try:
                await ingest(
                    prompt=prompt,
                    completion=completion,
                    total=total,
                    model=model or fallback_model,
                    application=application,
                    user_id=user_id,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    is_streaming=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Proxy ingest (stream) failed: %s", exc)

    return StreamingResponse(
        body_iter(),
        status_code=status_code,
        headers=resp_headers,
        media_type=media_type,
    )


class ProxyCollector(BaseCollector):
    def __init__(self):
        super().__init__("proxy")
        self.is_healthy = True
        self._server: Optional[uvicorn.Server] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if not settings.proxy_enabled:
            logger.info("ProxyCollector is disabled in settings.")
            return

        self.is_running = True
        app = _build_proxy_app(settings.proxy_target_url)
        config = uvicorn.Config(
            app,
            host=settings.host,
            port=settings.proxy_port,
            log_level=settings.log_level.lower(),
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve(), name="proxy-collector-server")
        logger.info(
            "ProxyCollector started on port %s -> %s",
            settings.proxy_port,
            settings.proxy_target_url,
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
        logger.info("ProxyCollector stopped.")

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.is_healthy,
            "port": settings.proxy_port if self.is_running else None,
            "target": settings.proxy_target_url,
        }
