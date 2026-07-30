"""FastAPI application exposing a sentiment analysis endpoint backed by Hugging Face."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.cache import get_cached, set_cached
from app.config import settings
from app.sentiment_client import SentimentServiceError, analyze_sentiment

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

app = FastAPI(
    title="Sentiment Analysis API",
    description="Connects to a Hugging Face model to classify text sentiment as POSITIVE or NEGATIVE.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze.")


class SentimentResponse(BaseModel):
    text: str
    label: str
    score: float
    cached: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sentiment", response_model=SentimentResponse)
@limiter.limit(settings.rate_limit)
def sentiment(request: Request, payload: SentimentRequest):
    text = payload.text.strip()
    if not text:
        return JSONResponse(status_code=400, content={"detail": "Field 'text' must not be empty or whitespace."})

    cached_result = get_cached(text)
    if cached_result is not None:
        return SentimentResponse(text=text, label=cached_result["label"], score=cached_result["score"], cached=True)

    try:
        result = analyze_sentiment(text)
    except SentimentServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    set_cached(text, result)
    return SentimentResponse(text=text, label=result["label"], score=result["score"], cached=False)
