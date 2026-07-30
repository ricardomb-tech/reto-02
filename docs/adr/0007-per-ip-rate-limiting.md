# ADR-0007: Per-IP rate limiting with slowapi, plus upstream backoff

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

Bonus B also asks for rate limiting. Two related but distinct concerns exist:

1. Protecting **this** service from being hammered by its own clients.
2. Handling the Hugging Face Inference API's own rate limit (`429`) and
   "model is loading" (`503`) responses gracefully, since the free tier is
   shared and can throttle or cold-start.

## Decision

- Incoming requests to `/sentiment` are rate-limited **per client IP** using
  `slowapi` (`app/main.py`), with a default of `10/minute`, configurable via
  the `RATE_LIMIT` environment variable. Requests over the limit receive an
  HTTP `429`.
- Calls to the upstream Hugging Face API retry automatically on `503` (model
  loading) with a short backoff, up to `MAX_RETRIES` attempts
  ([`app/sentiment_client.py`](../../app/sentiment_client.py)), and propagate a
  `429` transparently if Hugging Face itself is rate-limiting the request.

## Rationale

- Per-IP limiting is simple to reason about and requires no additional
  infrastructure (no external rate-limit store needed for a single-instance
  deployment), matching the scope of the challenge.
- Backing off on `503` avoids surfacing a spurious failure to the caller for a
  transient, well-documented Hugging Face behavior (cold model instances), and
  keeps `scripts/evaluate.py` runnable without manual retries.
- Making the service's own rate limit explicit protects the shared Hugging
  Face free-tier quota that all requests ultimately funnel through.

## Consequences

### Pros

- Both failure modes (this service overloaded vs. the upstream model
  overloaded/cold) are handled distinctly and documented in the README's error
  table.
- `scripts/evaluate.py` paces its own requests based on the configured
  `RATE_LIMIT`, so evaluating the sample dataset doesn't trip the limiter.

### Cons

- Per-IP limiting only works correctly with a fixed, addressable IP or one
  correctly forwarded via a reverse proxy; behind certain load balancers,
  extra "trusted proxy" configuration could be needed. Not relevant to the
  current single-instance deployment.
- A hardcoded retry cap (`MAX_RETRIES`) means a Hugging Face model that stays
  cold for longer than a few retries will still surface a `503` to the
  caller.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Global (non-per-IP) rate limit** | Would let one noisy client starve all others; per-IP limiting is a small addition via `slowapi` and is more fair. |
| **No retry on upstream `503`** | Would make the API unreliable for a normal user, since Hugging Face's free tier commonly cold-starts models that haven't been called recently. |
