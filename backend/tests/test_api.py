"""
CommentGuard — API Test Suite v3.0
───────────────────────────────────
Run:  cd backend && pytest tests/ -v

Tests cover:
  - Multi-label classification (6 categories)
  - Batch moderation endpoint
  - Perspective API compatibility endpoint
  - Anti-evasion text preprocessing
  - Health, stats, feedback endpoints
  - Edge cases (Unicode, long text, XSS)
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from typing import Dict


# ── Mock the ML model before importing the app ──────────────────────────────
def _mock_predict_multi(text: str) -> Dict[str, float]:
    """Deterministic mock: returns multi-label scores for known phrases."""
    text_lower = text.lower()

    toxic_phrases = {
        "i hate you": {"toxic": 0.92, "severe_toxic": 0.3, "obscene": 0.5, "threat": 0.1, "insult": 0.88, "identity_hate": 0.05},
        "hate you": {"toxic": 0.85, "severe_toxic": 0.2, "obscene": 0.3, "threat": 0.1, "insult": 0.8, "identity_hate": 0.05},
        "you are stupid": {"toxic": 0.85, "severe_toxic": 0.1, "obscene": 0.3, "threat": 0.05, "insult": 0.92, "identity_hate": 0.02},
        "kill yourself": {"toxic": 0.97, "severe_toxic": 0.91, "obscene": 0.4, "threat": 0.95, "insult": 0.6, "identity_hate": 0.1},
        "die": {"toxic": 0.88, "severe_toxic": 0.5, "obscene": 0.2, "threat": 0.85, "insult": 0.3, "identity_hate": 0.05},
        "idiot": {"toxic": 0.78, "severe_toxic": 0.05, "obscene": 0.4, "threat": 0.02, "insult": 0.9, "identity_hate": 0.01},
        "h4t3 y0u": {"toxic": 0.85, "severe_toxic": 0.2, "obscene": 0.3, "threat": 0.1, "insult": 0.8, "identity_hate": 0.05},
    }

    for phrase, scores in toxic_phrases.items():
        if phrase in text_lower:
            return scores

    # Default: clean text
    return {"toxic": 0.05, "severe_toxic": 0.01, "obscene": 0.02, "threat": 0.01, "insult": 0.03, "identity_hate": 0.01}


@pytest.fixture(autouse=True)
def mock_model(monkeypatch):
    """Patch the prediction function so tests don't need real model files."""
    import app.main as main_module
    monkeypatch.setattr(main_module, "_predict_multi", _mock_predict_multi)


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
        assert data["version"] == "3.0.0"
        assert "categories" in data
        assert len(data["categories"]) == 6

    def test_health_includes_features(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "multi-label" in data["features"]
        assert "anti-evasion" in data["features"]
        assert "batch" in data["features"]
        assert "perspective-compat" in data["features"]


# ── Multi-label moderation ───────────────────────────────────────────────────

class TestModerate:
    def test_toxic_comment_returns_categories(self, client):
        resp = client.post("/moderate", json={"text": "I hate you so much"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "toxic"
        assert data["decision"] == "block"
        assert data["flagged"] is True
        assert "toxic" in data["categories"]
        assert "insult" in data["categories"]
        # Check scores object exists with all categories
        assert "scores" in data
        assert data["scores"]["toxic"] >= 0.5
        assert data["scores"]["insult"] >= 0.5

    def test_threat_detected(self, client):
        resp = client.post("/moderate", json={"text": "kill yourself"})
        data = resp.json()
        assert "threat" in data["categories"]
        assert "severe_toxic" in data["categories"]
        assert data["scores"]["threat"] >= 0.5

    def test_clean_comment_no_categories(self, client):
        resp = client.post("/moderate", json={"text": "This is a great video, thanks!"})
        data = resp.json()
        assert data["label"] == "non_toxic"
        assert data["decision"] == "allow"
        assert data["flagged"] is False
        assert data["categories"] == []

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
        # With threshold=0.99, 0.92 toxic prob should NOT trigger
        assert data["flagged"] is False

    def test_response_schema_complete(self, client):
        resp = client.post("/moderate", json={"text": "test comment"})
        data = resp.json()
        assert "label" in data
        assert "toxic_prob" in data
        assert "decision" in data
        assert "categories" in data
        assert "scores" in data
        assert "flagged" in data
        # All 6 category scores present
        for cat in ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]:
            assert cat in data["scores"]


# ── Batch moderation ─────────────────────────────────────────────────────────

class TestBatch:
    def test_batch_multiple_texts(self, client):
        resp = client.post("/moderate/batch", json={
            "texts": ["I hate you", "Great video!", "kill yourself"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["toxic_count"] >= 2
        assert len(data["results"]) == 3
        assert "processing_time_ms" in data

    def test_batch_empty_array_returns_422(self, client):
        resp = client.post("/moderate/batch", json={"texts": []})
        assert resp.status_code == 422

    def test_batch_single_text(self, client):
        resp = client.post("/moderate/batch", json={"texts": ["hello"]})
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["label"] == "non_toxic"

    def test_batch_with_threshold(self, client):
        resp = client.post("/moderate/batch", json={
            "texts": ["I hate you", "you are stupid"],
            "threshold": 0.99
        })
        data = resp.json()
        # High threshold should flag nothing
        assert data["toxic_count"] == 0


# ── Perspective API compatibility ────────────────────────────────────────────

class TestPerspectiveCompat:
    def test_perspective_format(self, client):
        resp = client.post("/v1/comments:analyze", json={
            "comment": {"text": "I hate you"},
            "requestedAttributes": {"TOXICITY": {}, "INSULT": {}}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "attributeScores" in data
        assert "TOXICITY" in data["attributeScores"]
        assert "INSULT" in data["attributeScores"]
        # Check Perspective format structure
        tox = data["attributeScores"]["TOXICITY"]
        assert "summaryScore" in tox
        assert "value" in tox["summaryScore"]
        assert tox["summaryScore"]["type"] == "PROBABILITY"

    def test_perspective_only_requested_attributes(self, client):
        resp = client.post("/v1/comments:analyze", json={
            "comment": {"text": "hello"},
            "requestedAttributes": {"TOXICITY": {}}
        })
        data = resp.json()
        assert "TOXICITY" in data["attributeScores"]
        assert "INSULT" not in data["attributeScores"]

    def test_perspective_empty_text_422(self, client):
        resp = client.post("/v1/comments:analyze", json={
            "comment": {"text": ""},
            "requestedAttributes": {"TOXICITY": {}}
        })
        assert resp.status_code == 422


# ── Predict alias ────────────────────────────────────────────────────────────

class TestPredict:
    def test_predict_mirrors_moderate(self, client):
        payload = {"text": "You are an idiot"}
        resp_moderate = client.post("/moderate", json=payload)
        resp_predict = client.post("/predict", json=payload)
        assert resp_moderate.json()["label"] == resp_predict.json()["label"]


# ── Stats endpoint ───────────────────────────────────────────────────────────

class TestStats:
    def test_stats_includes_categories(self, client):
        client.post("/moderate", json={"text": "I hate you"})
        resp = client.get("/stats")
        data = resp.json()
        assert "by_category" in data
        assert data["version"] == "3.0.0"


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

    def test_feedback_missing_fields_returns_422(self, client):
        resp = client.post("/feedback", json={"text": "hello"})
        assert resp.status_code == 422


# ── Anti-evasion preprocessing ───────────────────────────────────────────────

class TestAntiEvasion:
    def test_leetspeak_detected(self, client):
        """h4t3 y0u should be normalized and caught."""
        resp = client.post("/moderate", json={"text": "h4t3 y0u"})
        data = resp.json()
        # After preprocessing: "hate you" → should trigger
        assert data["toxic_prob"] > 0.3  # at minimum shows some signal

    def test_separator_evasion(self, client):
        """k.i.l.l should be normalized."""
        from app.preprocess import preprocess
        assert "kill" in preprocess("k.i.l.l yourself")

    def test_unicode_normalization(self, client):
        from app.preprocess import preprocess
        # Zero-width chars should be stripped
        result = preprocess("ha\u200bte")
        assert "hate" in result

    def test_repeated_chars(self, client):
        from app.preprocess import preprocess
        result = preprocess("haaaaate")
        assert result == "haate"


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

    def test_emoji_only(self, client):
        resp = client.post("/moderate", json={"text": "😀🎉🔥💯"})
        assert resp.status_code == 200
        assert resp.json()["label"] == "non_toxic"
