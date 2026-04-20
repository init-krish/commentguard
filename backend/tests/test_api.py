"""
CommentGuard — API Test Suite
─────────────────────────────
Run:  cd backend && pytest tests/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── Mock the ML model before importing the app ──────────────────────────────
# This allows tests to run WITHOUT model files present.

def _mock_predict_prob(text: str) -> float:
    """Deterministic mock: returns high prob for known toxic phrases."""
    toxic_phrases = ["i hate you", "you are stupid", "kill yourself", "die", "idiot"]
    text_lower = text.lower()
    for phrase in toxic_phrases:
        if phrase in text_lower:
            return 0.92
    return 0.08


@pytest.fixture(autouse=True)
def mock_model(monkeypatch):
    """Patch the prediction function so tests don't need real model files."""
    import app.main as main_module
    monkeypatch.setattr(main_module, "_predict_prob", _mock_predict_prob)


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# ── Health check ─────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "model" in data
        assert "version" in data

    def test_health_includes_threshold(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "threshold" in data
        assert isinstance(data["threshold"], float)


# ── Moderation endpoint ─────────────────────────────────────────────────────

class TestModerate:
    def test_toxic_comment_is_blocked(self, client):
        resp = client.post("/moderate", json={"text": "I hate you so much"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "toxic"
        assert data["decision"] == "block"
        assert data["toxic_prob"] >= 0.5
        assert "toxic" in data["categories"]

    def test_clean_comment_is_allowed(self, client):
        resp = client.post("/moderate", json={"text": "This is a great video, thanks for sharing!"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "non_toxic"
        assert data["decision"] == "allow"
        assert data["toxic_prob"] < 0.5

    def test_empty_text_returns_422(self, client):
        resp = client.post("/moderate", json={"text": ""})
        assert resp.status_code == 422

    def test_missing_text_returns_422(self, client):
        resp = client.post("/moderate", json={})
        assert resp.status_code == 422

    def test_custom_threshold_override(self, client):
        resp = client.post("/moderate", json={
            "text": "I hate you",
            "threshold": 0.99
        })
        data = resp.json()
        # With threshold=0.99, a 0.92 prob should NOT be blocked
        assert data["decision"] != "block"

    def test_site_tag_accepted(self, client):
        resp = client.post("/moderate", json={
            "text": "Hello world",
            "site": "youtube"
        })
        assert resp.status_code == 200

    def test_response_schema(self, client):
        resp = client.post("/moderate", json={"text": "test comment"})
        data = resp.json()
        assert "label" in data
        assert "toxic_prob" in data
        assert "decision" in data
        assert "categories" in data
        assert isinstance(data["categories"], list)


# ── Predict endpoint (alias) ────────────────────────────────────────────────

class TestPredict:
    def test_predict_mirrors_moderate(self, client):
        payload = {"text": "You are an idiot"}
        resp_moderate = client.post("/moderate", json=payload)
        resp_predict = client.post("/predict", json=payload)
        # Both should return toxic
        assert resp_moderate.json()["label"] == resp_predict.json()["label"]


# ── Stats endpoint ───────────────────────────────────────────────────────────

class TestStats:
    def test_stats_returns_data(self, client):
        # Make a request first to populate stats
        client.post("/moderate", json={"text": "hello"})
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "toxic" in data
        assert "non_toxic" in data
        assert "toxic_rate" in data
        assert "model" in data


# ── Feedback endpoint ────────────────────────────────────────────────────────

class TestFeedback:
    def test_feedback_records_entry(self, client):
        resp = client.post("/feedback", json={
            "text": "This was flagged but is fine",
            "correct_label": "non_toxic",
            "predicted_label": "toxic"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "recorded"
        assert data["total_feedback"] >= 1

    def test_feedback_missing_fields_returns_422(self, client):
        resp = client.post("/feedback", json={"text": "hello"})
        assert resp.status_code == 422


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_very_long_comment(self, client):
        long_text = "word " * 5000
        resp = client.post("/moderate", json={"text": long_text})
        assert resp.status_code == 200

    def test_unicode_comment(self, client):
        resp = client.post("/moderate", json={"text": "你好世界 🌍 こんにちは"})
        assert resp.status_code == 200

    def test_special_characters(self, client):
        resp = client.post("/moderate", json={"text": "<script>alert('xss')</script>"})
        assert resp.status_code == 200
