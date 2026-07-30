from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sentiment_success():
    with patch("app.main.analyze_sentiment", return_value={"label": "POSITIVE", "score": 0.99}):
        response = client.post("/sentiment", json={"text": "I loved this movie!"})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "POSITIVE"
    assert body["score"] == 0.99
    assert body["cached"] is False


def test_sentiment_empty_text_rejected():
    response = client.post("/sentiment", json={"text": "   "})
    assert response.status_code == 400


def test_sentiment_missing_text_field():
    response = client.post("/sentiment", json={})
    assert response.status_code == 422


def test_sentiment_upstream_error_propagated():
    from app.sentiment_client import SentimentServiceError

    with patch("app.main.analyze_sentiment", side_effect=SentimentServiceError("boom", status_code=502)):
        response = client.post("/sentiment", json={"text": "some text"})
    assert response.status_code == 502
