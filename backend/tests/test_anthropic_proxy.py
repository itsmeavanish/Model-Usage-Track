"""Tests for the Anthropic proxy collector: SSE usage parsing + end-to-end capture."""
import json

import httpx
import pytest

from app.collectors.anthropic_proxy import (
    _AnthropicUsageAccumulator,
    _extract_nonstream_usage,
    _should_capture,
    _build_anthropic_proxy_app,
)

MODEL = "claude-sonnet-4-5-20250929"

SSE_STREAM = (
    'event: message_start\n'
    'data: {"type":"message_start","message":{"id":"msg_01","type":"message","role":"assistant","model":"'
    + MODEL +
    '","content":[],"stop_reason":null,"usage":{"input_tokens":25,"output_tokens":1,"cache_creation_input_tokens":100,"cache_read_input_tokens":50}}}\n\n'
    'event: content_block_start\n'
    'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n'
    'event: content_block_delta\n'
    'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}\n\n'
    'event: content_block_delta\n'
    'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}\n\n'
    'event: content_block_stop\n'
    'data: {"type":"content_block_stop","index":0}\n\n'
    'event: message_delta\n'
    'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":12}}\n\n'
    'event: message_stop\n'
    'data: {"type":"message_stop"}\n\n'
).encode()


def test_accumulator_extracts_usage_split_across_chunks():
    acc = _AnthropicUsageAccumulator()
    # Feed the stream in awkward 32-byte slices to test the line buffer.
    for i in range(0, len(SSE_STREAM), 32):
        acc.feed(SSE_STREAM[i:i + 32])
    res = acc.result(fallback_model="fallback")
    # input 25 + cache_creation 100 + cache_read 50 = 175 prompt tokens
    assert res["model"] == MODEL
    assert res["prompt_tokens"] == 175
    assert res["completion_tokens"] == 12
    assert res["total_tokens"] == 187
    assert res["metadata"]["cache_read_input_tokens"] == 50


def test_accumulator_handles_stream_with_no_usage():
    acc = _AnthropicUsageAccumulator()
    acc.feed(b'event: error\ndata: {"type":"error","error":{"type":"overloaded_error"}}\n\n')
    res = acc.result(fallback_model="claude-3")
    assert res["prompt_tokens"] == 0
    assert res["completion_tokens"] == 0
    assert res["total_tokens"] == 0
    assert res["model"] == "claude-3"


def test_nonstream_usage_extraction():
    body = {
        "id": "msg_01",
        "model": MODEL,
        "content": [{"type": "text", "text": "Hi"}],
        "usage": {
            "input_tokens": 25,
            "output_tokens": 12,
            "cache_creation_input_tokens": 100,
            "cache_read_input_tokens": 50,
        },
    }
    res = _extract_nonstream_usage(body, fallback_model=None)
    assert res["model"] == MODEL
    assert res["prompt_tokens"] == 175
    assert res["completion_tokens"] == 12
    assert res["total_tokens"] == 187


def test_should_capture_logic():
    assert _should_capture("v1/messages") is True
    # query strings / trailing path are fine
    assert _should_capture("v1/messages?beta=true") is True
    # count_tokens must NOT be captured (it returns hypothetical counts only)
    assert _should_capture("v1/messages/count_tokens") is False
    assert _should_capture("v1/models") is False


@pytest.mark.asyncio
async def test_proxy_captures_streaming_usage_end_to_end():
    captured: list[dict] = []

    def mock_upstream(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=SSE_STREAM
        )

    app = _build_anthropic_proxy_app(
        "https://api.anthropic.com",
        transport=httpx.MockTransport(mock_upstream),
        ingest=captured.append,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": MODEL, "stream": True, "messages": [{"role": "user", "content": "hi"}]},
        )
        # Drain the streamed body so the proxy generator finishes + ingests.
        _ = await resp.aread()

    assert resp.status_code == 200
    assert len(captured) == 1
    rec = captured[0]
    assert rec["provider"] == "anthropic"
    assert rec["source"] == "anthropic_proxy"
    assert rec["model"] == MODEL
    assert rec["total_tokens"] == 187
    assert rec["prompt_tokens"] == 175
    assert rec["completion_tokens"] == 12
    assert rec["is_streaming"] is True


@pytest.mark.asyncio
async def test_proxy_captures_nonstreaming_usage_end_to_end():
    captured: list[dict] = []
    body = {
        "id": "msg_01",
        "model": MODEL,
        "content": [{"type": "text", "text": "Hi"}],
        "usage": {"input_tokens": 25, "output_tokens": 12,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
    }

    def mock_upstream(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    app = _build_anthropic_proxy_app(
        "https://api.anthropic.com",
        transport=httpx.MockTransport(mock_upstream),
        ingest=captured.append,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": MODEL, "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    assert resp.json()["model"] == MODEL  # body forwarded intact
    assert len(captured) == 1
    rec = captured[0]
    assert rec["total_tokens"] == 37
    assert rec["completion_tokens"] == 12
    assert rec["is_streaming"] is False


@pytest.mark.asyncio
async def test_proxy_does_not_capture_count_tokens():
    captured: list[dict] = []

    def mock_upstream(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"input_tokens": 42})

    app = _build_anthropic_proxy_app(
        "https://api.anthropic.com",
        transport=httpx.MockTransport(mock_upstream),
        ingest=captured.append,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/messages/count_tokens", json={"model": MODEL, "messages": []})

    assert resp.status_code == 200
    assert captured == []  # count_tokens must never be metered
