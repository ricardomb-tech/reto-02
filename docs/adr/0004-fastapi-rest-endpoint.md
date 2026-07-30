# ADR-0004: Expose the solution as a FastAPI REST endpoint

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge requires exposing the solution either as a Flask/FastAPI
endpoint or as a CLI script. Both approaches would satisfy the base
requirement.

## Decision

The solution is exposed as a **FastAPI** application
([`app/main.py`](../../app/main.py)) with `GET /health` and `POST /sentiment`
endpoints, rather than as a CLI script or a Flask app.

## Rationale

- FastAPI provides request validation (via Pydantic models) and automatic
  interactive documentation (Swagger UI at `/docs`) with very little
  boilerplate, which helps a judge exercise the API without extra tooling.
- Native support for dependency injection and middleware made it
  straightforward to wire in `slowapi` for per-IP rate limiting
  ([ADR-0007](0007-per-ip-rate-limiting.md)).
- An HTTP endpoint is easier to demo end-to-end (e.g. with `curl`, `scripts/evaluate.py`,
  or a container health check) than a CLI script, and maps naturally onto the
  Docker bonus ([ADR-0006](0006-in-memory-ttl-cache.md) and the Dockerfile).

## Consequences

### Pros

- Self-documenting API (`/docs`, `/openapi.json`) with typed request/response
  validation out of the box.
- Straightforward to containerize (Bonus A) and to protect with rate limiting
  and caching (Bonus B).

### Cons

- Requires running a persistent server process, versus a CLI script that
  could be invoked once and exit — slightly more moving parts for a judge to
  start up (though a single `uvicorn` command is enough).

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Flask** | Would require adding a separate validation library (e.g. `marshmallow` or manual checks) and a separate rate-limiting extension; FastAPI provides both more directly via Pydantic and `slowapi`. |
| **CLI script** | Simpler to write, but harder to demonstrate the caching and rate-limiting bonus in a way that's visible to a judge (an HTTP response header/field is more explicit than console output). |
