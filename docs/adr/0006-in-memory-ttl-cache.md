# ADR-0006: In-memory TTL cache for repeated requests (Bonus B)

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

Bonus B asks for caching and rate limiting. Repeated identical requests to
`/sentiment` should not need to call the Hugging Face API again, both to
reduce latency and to conserve the free API quota.

## Decision

A simple **in-memory TTL cache** was implemented in
[`app/cache.py`](../../app/cache.py) using `cachetools.TTLCache`, keyed by the
SHA-256 hash of the normalized (trimmed, lower-cased) input text. Default TTL
is 1 hour and max size is 1000 entries, both configurable via
`CACHE_TTL_SECONDS` / `CACHE_MAX_SIZE`.

## Rationale

- The service is a single-process demo/API for a coding challenge, not a
  multi-instance production deployment — an in-memory cache is sufficient and
  requires no extra infrastructure (e.g. Redis) to run or to review.
- Hashing the normalized text keeps memory bounded and avoids storing raw
  user text as a dictionary key indefinitely (bounded by `CACHE_MAX_SIZE` with
  LRU-style eviction from `cachetools`).
- The response includes a `"cached": true/false` field, making the caching
  behavior directly observable to a judge via `curl`, rather than only
  inferable from latency.

## Consequences

### Pros

- Zero extra infrastructure/dependencies beyond the `cachetools` package.
- Directly testable and observable through the API response itself.

### Cons

- Cache is per-process and lost on restart; it would not be shared across
  multiple replicas in a horizontally scaled deployment.
- Not persisted, so a fresh container (e.g. after a Docker restart) starts
  with a cold cache.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Redis-backed cache** | Would require an extra service/container and connection configuration, adding operational complexity disproportionate to a single-instance challenge submission. |
| **No caching** | Would not satisfy Bonus B and would call the rate-limited Hugging Face API on every repeated request. |
