# ADR-0007: Per-IP rate limiting with slowapi, plus upstream backoff

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

Bonus B also asks for rate limiting, and there are really two separate
problems here:

1. Protecting **this** service from being hammered by its own clients.
2. Handling the Hugging Face Inference API's own rate limit (`429`) and
   "model is loading" (`503`) responses gracefully, since the free tier is
   shared and can throttle or cold-start on you.

## Decision

- Requests to `/sentiment` are rate-limited **per client IP** using
  `slowapi` (`app/main.py`), 10/minute by default, configurable through the
  `RATE_LIMIT` environment variable. Go over the limit and you get an HTTP
  `429`.
- Calls to the upstream Hugging Face API retry automatically on `503`
  (model loading) with a short backoff, up to `MAX_RETRIES` attempts
  ([`app/sentiment_client.py`](../../app/sentiment_client.py)), and pass a
  `429` straight through if Hugging Face itself is rate-limiting the
  request.

## Rationale

- Per-IP limiting is easy to reason about and needs no extra infrastructure
  (no external rate-limit store for a single-instance deployment), which
  matches the scope of the challenge.
- Backing off on `503` avoids surfacing a spurious failure for what's really
  a well-known, transient Hugging Face behavior (cold model instances), and
  keeps `scripts/evaluate.py` runnable without manual retries.
- Making the service's own rate limit explicit protects the shared Hugging
  Face free-tier quota that every request ultimately funnels through.

## Consequences

### Pros

- Both failure modes, this service overloaded versus the upstream model
  overloaded or cold, are handled separately and documented in the README's
  error table.
- `scripts/evaluate.py` paces its own requests based on the configured
  `RATE_LIMIT`, so running it against the sample dataset doesn't trip the
  limiter.

### Cons

- Per-IP limiting only works cleanly with a fixed, addressable IP, or one
  correctly forwarded through a reverse proxy. Behind certain load
  balancers, you'd need extra "trusted proxy" config. Not a concern for the
  current single-instance deployment.
- The retry cap (`MAX_RETRIES`) is hardcoded, so a model that stays cold
  longer than a few retries will still surface a `503` to the caller.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Global (non-per-IP) rate limit** | Would let one noisy client starve everyone else. Per-IP limiting is a small addition through `slowapi` and is just more fair. |
| **No retry on upstream `503`** | Would make the API flaky for a normal user, since Hugging Face's free tier commonly cold-starts models that haven't been called in a while. |
