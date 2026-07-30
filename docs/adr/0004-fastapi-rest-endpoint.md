# ADR-0004: Expose the solution as a FastAPI REST endpoint

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge asks for either a Flask/FastAPI endpoint or a CLI script.
Either would satisfy the base requirement.

## Decision

I exposed the solution as a **FastAPI** application
([`app/main.py`](../../app/main.py)) with `GET /health` and `POST /sentiment`
endpoints, instead of a CLI script or a Flask app.

## Rationale

- FastAPI gives me request validation through Pydantic and automatic
  interactive docs (Swagger UI at `/docs`) with almost no boilerplate. That
  means a judge can poke at the API without installing anything extra.
- Its dependency injection and middleware support made it easy to wire in
  `slowapi` for per-IP rate limiting
  ([ADR-0007](0007-per-ip-rate-limiting.md)).
- An HTTP endpoint is simpler to demo end to end, with `curl`,
  `scripts/evaluate.py`, or a container health check, than a CLI script
  would be, and it fits naturally with the Docker bonus
  ([ADR-0006](0006-in-memory-ttl-cache.md) and the Dockerfile).

## Consequences

### Pros

- Self-documenting API (`/docs`, `/openapi.json`) with typed request and
  response validation built in.
- Easy to containerize (Bonus A) and to protect with rate limiting and
  caching (Bonus B).

### Cons

- It needs a persistent server process running, unlike a CLI script you
  could invoke once and walk away from. One more moving part for a judge to
  start up, though a single `uvicorn` command covers it.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Flask** | Would need a separate validation library (`marshmallow`, or hand-rolled checks) and a separate rate-limiting extension. FastAPI gives me both through Pydantic and `slowapi` already. |
| **CLI script** | Quicker to write, but harder to show off the caching and rate-limiting bonus in a way a judge can actually see. An HTTP response field is more visible than console output. |
