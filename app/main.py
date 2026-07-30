"""FastAPI application exposing a sentiment analysis endpoint backed by Hugging Face."""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.cache import get_cached, set_cached
from app.config import settings
from app.logging_config import configure_logging, logger
from app.sentiment_client import (
    SentimentServiceError,
    analyze_sentiment,
    analyze_sentiment_batch,
    close_http_client,
    prewarm_model,
)

configure_logging()

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire-and-forget: wake up the model on Hugging Face's side without delaying startup.
    app.state.prewarm_task = asyncio.create_task(prewarm_model())
    yield
    await close_http_client()


app = FastAPI(
    title="Sentiment Analysis API",
    description="Connects to a Hugging Face model to classify text sentiment as POSITIVE or NEGATIVE.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
Instrumentator().instrument(app).expose(app, include_in_schema=False)

_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.is_dir():
    app.mount("/demo", StaticFiles(directory=_static_dir, html=True), name="demo")


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_body_bytes:
        return JSONResponse(status_code=413, content={"detail": "Payload too large."})
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/demo"):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'",
        )
    return response


@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    request_id = uuid.uuid4().hex
    started = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request handled",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze.")


class SentimentResponse(BaseModel):
    text: str
    label: str
    score: float
    cached: bool


class BatchSentimentRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=settings.batch_max_size)


class BatchSentimentResponse(BaseModel):
    results: list[SentimentResponse]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sentiment", response_model=SentimentResponse)
@limiter.limit(settings.rate_limit)
async def sentiment(request: Request, payload: SentimentRequest):
    text = payload.text.strip()
    if not text:
        return JSONResponse(status_code=400, content={"detail": "Field 'text' must not be empty or whitespace."})

    cached_result = await get_cached(text)
    if cached_result is not None:
        return SentimentResponse(text=text, label=cached_result["label"], score=cached_result["score"], cached=True)

    try:
        result = await analyze_sentiment(text)
    except SentimentServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    await set_cached(text, result)
    return SentimentResponse(text=text, label=result["label"], score=result["score"], cached=False)


@app.post("/sentiment/batch", response_model=BatchSentimentResponse)
@limiter.limit(settings.batch_rate_limit)
async def sentiment_batch(request: Request, payload: BatchSentimentRequest):
    texts = [t.strip() for t in payload.texts]
    if any(not t for t in texts):
        return JSONResponse(status_code=400, content={"detail": "Every entry in 'texts' must be non-empty."})

    results: list[dict | None] = [None] * len(texts)
    pending_indices = []
    pending_texts = []

    for i, text in enumerate(texts):
        cached_result = await get_cached(text)
        if cached_result is not None:
            results[i] = {**cached_result, "cached": True}
        else:
            pending_indices.append(i)
            pending_texts.append(text)

    if pending_texts:
        try:
            fresh_results = await analyze_sentiment_batch(pending_texts)
        except SentimentServiceError as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

        for i, text, result in zip(pending_indices, pending_texts, fresh_results):
            await set_cached(text, result)
            results[i] = {**result, "cached": False}

    return BatchSentimentResponse(
        results=[SentimentResponse(text=text, **result) for text, result in zip(texts, results)]
    )
