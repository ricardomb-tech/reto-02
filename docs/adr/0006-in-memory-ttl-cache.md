# ADR-0006: In-memory TTL cache for repeated requests (Bonus B)

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

Bonus B asks for caching and rate limiting. Repeated identical requests to
`/sentiment` shouldn't need to hit the Hugging Face API again, both to cut
latency and to avoid burning through the free API quota.

## Decision

I built a simple **in-memory TTL cache** in
[`app/cache.py`](../../app/cache.py) using `cachetools.TTLCache`, keyed by
the SHA-256 hash of the normalized (trimmed, lower-cased) input text. Default
TTL is 1 hour, max size is 1000 entries, both configurable through
`CACHE_TTL_SECONDS` / `CACHE_MAX_SIZE`.

## Rationale

- This is a single-process demo API for a coding challenge, not a
  multi-instance production deployment. An in-memory cache is enough and
  needs no extra infrastructure (Redis, say) to run or to review.
- Hashing the normalized text keeps memory bounded, and I'm not storing raw
  user text as a dictionary key forever, `cachetools` evicts once
  `CACHE_MAX_SIZE` is hit.
- The response includes a `"cached": true/false` field, so the caching
  behavior is something a judge can actually see via `curl`, not just infer
  from latency.

## Consequences

### Pros

- Zero extra infrastructure beyond the `cachetools` package.
- Directly testable and visible through the API response itself.

### Cons

- The cache is per-process and disappears on restart. It wouldn't be shared
  across replicas in a horizontally scaled deployment.
- Nothing is persisted, so a fresh container (after a Docker restart, say)
  starts cold.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Redis-backed cache** | Needs an extra service and connection config, more operational weight than a single-instance challenge submission calls for. |
| **No caching** | Wouldn't satisfy Bonus B, and would hit the rate-limited Hugging Face API on every repeated request. |
