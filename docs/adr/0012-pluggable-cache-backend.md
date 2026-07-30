# ADR-0012: Pluggable cache backend (in-memory default, optional Redis)

- **Status:** Accepted
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

ADR-0006 chose an in-memory TTL cache because this is a single-process
demo/API for a coding challenge, and explicitly called out that it "would
not be shared across multiple replicas in a horizontally scaled
deployment" as a known limitation. That's still true today, but nothing
stops the cache from being designed so that scaling out doesn't require a
rewrite later.

## Decision

`app/cache.py` is now a thin facade over a `CacheBackend` interface defined
in [`app/cache_backends.py`](../../app/cache_backends.py): `get`/`set`, both
`async`. Two implementations exist: `InMemoryCacheBackend` (today's
`cachetools.TTLCache` logic, unchanged behavior) and `RedisCacheBackend`
(stores JSON-encoded results with `SETEX` via `redis.asyncio`). Which one
runs is chosen by `CACHE_BACKEND=memory|redis` (default `memory`), with
`REDIS_URL` pointing at the Redis instance when selected.

## Rationale

- Nothing changes for anyone who doesn't set `CACHE_BACKEND`: same
  in-memory behavior, same defaults, no new required infrastructure.
- Making `get`/`set` `async` (rather than sync, as before) means the Redis
  backend does real non-blocking I/O instead of a sync call stalling the
  event loop; the in-memory backend just wraps a dict lookup in an `async`
  function, which costs nothing.
- Importing `redis.asyncio` lazily, inside `RedisCacheBackend.__init__`,
  means the `redis` package is only actually exercised if `CACHE_BACKEND=redis`
  is set. Nobody running the default configuration depends on it being
  reachable, or even correctly configured.
- This directly extends ADR-0006 rather than reversing it: the "con" it
  documented (no cross-replica sharing) now has an opt-in answer instead of
  staying a permanent limitation.

## Consequences

### Pros

- Horizontal scaling becomes a config change (`CACHE_BACKEND=redis` +
  `REDIS_URL`), not a rewrite of `app/main.py` or the cache call sites.
- `tests/test_cache_backend.py` covers the in-memory backend fully and the
  backend-selection logic without needing Redis running; a live
  round-trip test against real Redis is included but skips itself
  cleanly (`pytest.mark.skipif`) when no Redis is reachable.

### Cons

- The Redis path is untested in CI unless a Redis instance is actually
  running there; it's verified by hand and by a self-skipping test, not by
  a guaranteed CI run.
- Redis-side failures (connection refused, timeout) aren't specifically
  handled the way Hugging Face failures are (ADR-0007/0010); a
  `RedisCacheBackend` outage would currently surface as an unhandled
  exception rather than a graceful fallback to "treat as a cache miss."

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Require Redis unconditionally** | Reverses ADR-0006's whole point: no required infrastructure for a single-instance challenge submission. |
| **Keep the cache in-memory only, document Redis as a "future work" idea** | That's what ADR-0006 already did; this ADR exists to actually close that gap instead of leaving it as a permanent aspiration. |
