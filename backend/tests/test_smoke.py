"""Smoke test: app boots, lifespan creates tables, key routes return 200."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analytics_summary_empty(client):
    resp = client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_requests"] == 0
    assert body["total_tokens"] == 0


def test_analytics_me_vs_total(client):
    resp = client.get("/api/v1/analytics/me-vs-total")
    assert resp.status_code == 200
    body = resp.json()
    assert body["identity"] == "me@example.com"
    assert "mine" in body and "total" in body and "trends" in body


def test_collectors_status(client):
    resp = client.get("/api/v1/collectors/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "official" in body
    assert "webhook" in body


def test_webhook_ingest_and_request_list(client):
    payload = {
        "request_id": "smoke-req-1",
        "model": "glm-5.2",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "application": "opencode",
        "user_id": "me@example.com",
    }
    r = client.post("/api/v1/webhook/ingest", json=payload)
    assert r.status_code == 200
    assert r.json()["request_id"] == "smoke-req-1"

    # It shows up in the requests list and analytics
    lst = client.get("/api/v1/requests/").json()
    assert any(x["request_id"] == "smoke-req-1" for x in lst)

    summary = client.get("/api/v1/analytics/summary").json()
    assert summary["total_requests"] >= 1
    assert summary["total_tokens"] >= 150

    by_user = client.get("/api/v1/analytics/by-user").json()
    assert any(u["name"] == "me@example.com" for u in by_user)
