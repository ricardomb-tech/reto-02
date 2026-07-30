# ADR-0008: Async HTTP client and a batch endpoint for latency and throughput

- **Status:** Accepted
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

The original implementation called Hugging Face with the synchronous
`requests` library from a sync route handler. That works, but it means one
in-flight request to Hugging Face ties up a worker thread, and evaluating
many texts (`scripts/evaluate.py` against `data/sample_reviews.csv`) means
one HTTP round trip per row. `httpx==0.27.0` was already sitting in
`requirements.txt`, pulled in only for FastAPI's `TestClient`, and never
actually used to talk to Hugging Face.

## Decision

I moved `app/sentiment_client.py` to a shared `httpx.AsyncClient`, made
`analyze_sentiment` and the `/sentiment` route `async def`, and added a
second endpoint, `POST /sentiment/batch`, that sends a whole list of texts
to Hugging Face in a single call via `analyze_sentiment_batch`. I also added
a best-effort pre-warm call on startup (`prewarm_model`, fired with
`asyncio.create_task` so it never blocks the app from becoming ready) to
nudge Hugging Face into loading the model before real traffic shows up.

## Rationale

- `httpx.AsyncClient` reuses a connection pool across requests instead of
  opening a new TCP/TLS connection per call, which matters once you're
  calling Hugging Face repeatedly.
- An async route frees the worker thread while waiting on the network,
  instead of blocking it, which is the whole point of running under
  `uvicorn`.
- Hugging Face's inference endpoint already accepts a list under
  `"inputs"` and returns one result per item, so a batch endpoint is a
  thin addition, not a new integration.
- Pre-warming turns "the first real request eats the `503` cold-start
  penalty" into "the app absorbed that cost during startup instead."

## Consequences

### Pros

- `scripts/evaluate.py --batch` sends the entire sample CSV in one HTTP
  call instead of 20, and reports wall-clock time next to the per-row mode
  so the latency difference is a number a judge can see, not a claim.
- No new dependency: `httpx` was already installed.

### Cons

- `/sentiment/batch` is one more surface to keep in sync with `/sentiment`
  (rate limits, caching, error handling), and I capped it at
  `BATCH_MAX_SIZE` (50 texts) so one request can't turn into an
  unbounded Hugging Face call.
- The pre-warm call spends one Hugging Face request on startup for a
  throwaway string, which technically counts against the free-tier quota.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Keep `requests`, add a thread pool for concurrency** | Works, but reinvents what an async HTTP client already gives you, and `httpx` was already a dependency. |
| **No batch endpoint, just let clients call `/sentiment` in a loop** | Simple, but throws away the one-call-for-many-texts option Hugging Face's API already supports, and it's the more interesting demo of throughput. |
