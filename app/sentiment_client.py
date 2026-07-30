"""Client for calling the Hugging Face Inference API for sentiment analysis."""
import asyncio

import httpx

from app.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.config import settings


class SentimentServiceError(Exception):
    """Raised when the upstream Hugging Face API cannot fulfill the request."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


_breaker = CircuitBreaker(
    failure_threshold=settings.circuit_breaker_threshold,
    reset_seconds=settings.circuit_breaker_reset_seconds,
)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    return _client


async def close_http_client() -> None:
    """Close the shared HTTP client. Call this from the app's shutdown handler."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _headers() -> dict:
    if not settings.hf_api_token:
        raise SentimentServiceError(
            "Server misconfigured: HF_API_TOKEN environment variable is not set.",
            status_code=500,
        )
    return {"Authorization": f"Bearer {settings.hf_api_token}"}


def _best_from_scores(scores: list) -> dict:
    """Pick the highest-confidence label out of Hugging Face's per-label score list.

    Binary softmax confidence is always >= 0.5, so a low score means the model wasn't
    really sure either way. Below `neutral_confidence_threshold`, report NEUTRAL instead
    of forcing the call into POSITIVE/NEGATIVE (see ADR-0009).
    """
    try:
        best = max(scores, key=lambda item: item["score"])
        label = best["label"]
        score = round(float(best["score"]), 4)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise SentimentServiceError(f"Unexpected response shape from model: {scores}") from exc

    if score < settings.neutral_confidence_threshold:
        label = "NEUTRAL"
    return {"label": label, "score": score}


def _parse_single_result(payload) -> dict:
    # Expected shape: [[{"label": "POSITIVE", "score": 0.99}, {"label": "NEGATIVE", "score": 0.01}]]
    try:
        scores = payload[0]
    except (KeyError, IndexError, TypeError) as exc:
        raise SentimentServiceError(f"Unexpected response shape from model: {payload}") from exc
    return _best_from_scores(scores)


def _parse_batch_result(payload) -> list:
    # Expected shape: one scores-list per input text.
    if not isinstance(payload, list):
        raise SentimentServiceError(f"Unexpected response shape from model: {payload}")
    return [_best_from_scores(scores) for scores in payload]


async def _call_hf(inputs):
    """POST to the Hugging Face Inference API, retrying on a cold ("model loading") response."""
    try:
        _breaker.before_call()
    except CircuitBreakerOpenError as exc:
        raise SentimentServiceError(str(exc), status_code=503) from exc

    try:
        result = await _call_hf_with_retries(inputs)
    except SentimentServiceError:
        _breaker.record_failure()
        raise
    _breaker.record_success()
    return result


async def _call_hf_with_retries(inputs):
    last_error: SentimentServiceError | None = None
    client = _get_client()

    for attempt in range(1, settings.max_retries + 1):
        try:
            response = await client.post(
                settings.hf_api_url,
                headers=_headers(),
                json={"inputs": inputs, "options": {"wait_for_model": True}},
            )
        except httpx.TimeoutException:
            last_error = SentimentServiceError("Timed out waiting for the sentiment model.", status_code=504)
            continue
        except httpx.RequestError as exc:
            raise SentimentServiceError(f"Could not reach the sentiment model service: {exc}") from exc

        if response.status_code == 200:
            return response.json()

        if response.status_code == 503:
            # Model is loading on Hugging Face's side; back off and retry.
            wait_seconds = min(response.json().get("estimated_time", 2), 10) if response.content else 2
            last_error = SentimentServiceError(
                "The sentiment model is still loading upstream. Please retry shortly.", status_code=503
            )
            await asyncio.sleep(wait_seconds)
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


async def analyze_sentiment(text: str) -> dict:
    """Call the Hugging Face Inference API and return {"label", "score"} for one text."""
    payload = await _call_hf(text)
    return _parse_single_result(payload)


async def analyze_sentiment_batch(texts: list) -> list:
    """Call the Hugging Face Inference API once for a list of texts, in order."""
    payload = await _call_hf(texts)
    return _parse_batch_result(payload)


async def prewarm_model() -> None:
    """Best-effort call to wake up the model on Hugging Face's side before real traffic arrives."""
    try:
        await analyze_sentiment("warm up")
    except SentimentServiceError:
        pass
