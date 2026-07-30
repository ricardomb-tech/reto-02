# ADR-0010: In-process circuit breaker for upstream resilience

- **Status:** Accepted
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

ADR-0007 already retries a Hugging Face `503` (model loading) a few times
before giving up. That's fine for a transient cold start, but it doesn't
help if Hugging Face is genuinely down, or the token is wrong, for a
stretch of time: every request would still pay the full retry cost before
failing, one request at a time, for as long as the outage lasts.

## Decision

I added a small, dependency-free circuit breaker
([`app/circuit_breaker.py`](../../app/circuit_breaker.py)) around the
Hugging Face call in `_call_hf` (`app/sentiment_client.py`). After
`CIRCUIT_BREAKER_THRESHOLD` consecutive failures (default 5), it opens and
new requests fail fast with a `503` instead of retrying against a service
that's already failing. After `CIRCUIT_BREAKER_RESET_SECONDS` (default 30),
it lets one trial call through; success closes it again, failure keeps it
open.

## Rationale

- Failing fast during an outage is cheaper for both this service and
  Hugging Face's already-struggling endpoint than every request separately
  retrying and timing out.
- A hand-rolled breaker is a small state machine (closed/open/half-open); it
  didn't need a library like `pybreaker`, matching the project's existing
  preference for no unnecessary infrastructure (ADR-0006).
- Wrapping it around `_call_hf` means both `/sentiment` and
  `/sentiment/batch` get the same protection for free.

## Consequences

### Pros

- During a real Hugging Face outage, the service degrades to fast `503`s
  instead of every request hanging through a full retry cycle.
- The breaker's state machine is unit-testable in isolation
  (`tests/test_circuit_breaker.py`), no network or mocking required.

### Cons

- It's a single, process-wide breaker; a second replica in a scaled
  deployment would track its own state independently, so it doesn't
  coordinate across instances.
- The threshold treats every kind of failure the same way (network error,
  `429`, `401`), so a wrong `HF_API_TOKEN` trips the same breaker as a real
  outage would.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **`pybreaker` or another circuit-breaker library** | Adds a dependency for a state machine of maybe 40 lines; not worth it at this scale. |
| **No circuit breaker, rely only on the existing retry/backoff** | Retries handle a cold model fine, but they don't stop a service from hammering a genuinely down upstream one request at a time. |
