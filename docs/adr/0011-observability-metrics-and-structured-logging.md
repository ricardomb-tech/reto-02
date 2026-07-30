# ADR-0011: Observability - Prometheus metrics and structured logging

- **Status:** Accepted
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

Every claim this project makes about caching (ADR-0006), rate limiting
(ADR-0007), and now the circuit breaker (ADR-0010) was only checkable by
reading the response body or timing requests by hand. There was no place
to see, over time, how often the cache actually gets hit, how often the
breaker trips, or what a request even looked like once it left the
terminal.

## Decision

- `/metrics` is exposed via `prometheus-fastapi-instrumentator`
  (`app/main.py`), giving request count, latency, and in-progress requests
  for free.
- Three custom counters make the existing claims verifiable:
  `sentiment_cache_hits_total` / `sentiment_cache_misses_total`
  (`app/cache.py`) and `sentiment_circuit_breaker_trips_total`
  (`app/circuit_breaker.py`).
- Logging moved from nothing to structured JSON lines
  (`app/logging_config.py`, stdlib `logging`, no new dependency), through a
  middleware in `main.py` that stamps every request with a `request_id`
  (also echoed back as `X-Request-ID`), method, path, status code, and
  duration.

## Rationale

- `prometheus-fastapi-instrumentator` wires up the standard HTTP metrics in
  a couple of lines instead of hand-rolling histograms.
- The custom counters are cheap (one `.inc()` call) and turn "we have
  caching" and "we have a circuit breaker" into numbers a judge, or anyone
  running this in production, can actually watch.
- JSON logs are what you'd forward to any log aggregator without a second
  parsing step, and a request ID is what lets you find one request's story
  across log lines, so I added both instead of leaving `print`-style output
  in place.
- Sticking to the stdlib for logging (no `structlog`, no extra library)
  keeps the same "minimal dependencies" stance as the caching and
  rate-limiting decisions.

## Consequences

### Pros

- `/metrics` is scrapeable by any standard Prometheus setup with zero
  extra configuration.
- Every log line is machine-parseable and traceable to a single request via
  `request_id`.

### Cons

- `/metrics` is unauthenticated and world-readable on whatever port the API
  runs on; fine for a challenge submission or an internal network, not
  something I'd expose publicly as-is in a real deployment.
- The custom counters only exist in-process. Like the cache and the
  breaker, they reset whenever the process restarts and aren't aggregated
  across replicas without an external Prometheus setup doing that job.
- Installing `prometheus-fastapi-instrumentator` pulled in a newer
  `starlette` release that broke `fastapi==0.111.0` outright (a
  `Router.__init__()` signature change). I pinned `starlette==0.37.2`
  explicitly in `requirements.txt` and downgraded to
  `prometheus-fastapi-instrumentator==7.1.0`, which stays compatible - a
  reminder that an unpinned transitive dependency can break a pinned one.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **OpenTelemetry (metrics + tracing)** | More powerful, but means running or pointing at a collector; disproportionate for a single-instance challenge submission. |
| **`structlog` for logging** | A stdlib `JsonFormatter` gets the same structured-log outcome without adding a dependency. |
