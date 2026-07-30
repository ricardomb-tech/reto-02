"""Client for calling the Hugging Face Inference API for sentiment analysis."""
import time

import requests

from app.config import settings


class SentimentServiceError(Exception):
    """Raised when the upstream Hugging Face API cannot fulfill the request."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _headers() -> dict:
    if not settings.hf_api_token:
        raise SentimentServiceError(
            "Server misconfigured: HF_API_TOKEN environment variable is not set.",
            status_code=500,
        )
    return {"Authorization": f"Bearer {settings.hf_api_token}"}


def _parse_result(payload) -> dict:
    # Expected shape: [[{"label": "POSITIVE", "score": 0.99}, {"label": "NEGATIVE", "score": 0.01}]]
    try:
        scores = payload[0]
        best = max(scores, key=lambda item: item["score"])
        return {"label": best["label"], "score": round(float(best["score"]), 4)}
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise SentimentServiceError(f"Unexpected response shape from model: {payload}") from exc


def analyze_sentiment(text: str) -> dict:
    """Call the Hugging Face Inference API and return {"label", "score"} for the given text."""
    last_error: SentimentServiceError | None = None

    for attempt in range(1, settings.max_retries + 1):
        try:
            response = requests.post(
                settings.hf_api_url,
                headers=_headers(),
                json={"inputs": text, "options": {"wait_for_model": True}},
                timeout=settings.request_timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            last_error = SentimentServiceError("Timed out waiting for the sentiment model.", status_code=504)
            continue
        except requests.exceptions.RequestException as exc:
            raise SentimentServiceError(f"Could not reach the sentiment model service: {exc}") from exc

        if response.status_code == 200:
            return _parse_result(response.json())

        if response.status_code == 503:
            # Model is loading on Hugging Face's side; back off and retry.
            wait_seconds = min(response.json().get("estimated_time", 2), 10) if response.content else 2
            last_error = SentimentServiceError(
                "The sentiment model is still loading upstream. Please retry shortly.", status_code=503
            )
            time.sleep(wait_seconds)
            continue

        if response.status_code == 429:
            raise SentimentServiceError(
                "Hugging Face API rate limit exceeded. Please slow down and try again later.", status_code=429
            )

        if response.status_code == 401:
            raise SentimentServiceError(
                "Hugging Face API rejected the request: invalid or missing HF_API_TOKEN.", status_code=401
            )

        raise SentimentServiceError(
            f"Hugging Face API returned an unexpected error ({response.status_code}): {response.text}",
            status_code=502,
        )

    raise last_error or SentimentServiceError("Failed to get a sentiment result after retries.")
