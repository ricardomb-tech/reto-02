# ADR-0013: Security hardening from an internal audit

- **Status:** Accepted
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

I ran a full audit of the project (dependency/SCA review, static code analysis,
secret scanning, configuration/Docker review, and CI/supply-chain review)
before treating the submission as done. Most of it came back clean, no
critical or high-severity findings, but a handful of real, fixable gaps
turned up, plus a couple of things worth writing down as consciously
accepted risk rather than silently ignored.

## Decision

### Fixed

- **Security response headers** (`app/main.py`): every response now gets
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and
  `Referrer-Policy: no-referrer`. `/demo` additionally gets a
  `Content-Security-Policy` restricting scripts/styles to `'self'`, since
  it's the only route serving actual HTML with an inline `<script>`.
- **Request body size cap** (`app/main.py`, `app/config.py`): requests over
  `MAX_REQUEST_BODY_BYTES` (default 256 KB) are rejected with `413` before
  the body is read, so an oversized payload can't be fully buffered and
  parsed before Pydantic's `max_length` ever gets a chance to reject it.
- **`static/index.html`** no longer uses `innerHTML` with template
  literals to render the API response. It builds the result with
  `createElement`/`textContent` instead. The old code wasn't exploitable
  today (`label` only ever holds a fixed enum value, `detail` is never the
  user's own text), but `innerHTML` on API-controlled data is exactly the
  pattern that turns into real XSS the moment a response field changes.
- **Dockerfile**: added a non-root `appuser` (previously the container ran
  as root) and a `HEALTHCHECK` that hits the existing `GET /health`
  endpoint, so a hung container gets detected instead of looking "up"
  forever.
- **`.gitignore`**: added `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`,
  `id_rsa`, `id_ed25519`, `credentials.json`, `service-account*.json`,
  `.npmrc`, `.pypirc` as defense in depth. None of these exist in the repo
  today; this just makes sure one never gets committed by accident later.
- **CI** (`.github/workflows/ci.yml`): added an explicit
  `permissions: contents: read` (the workflow never needed more), pinned
  `actions/checkout` and `actions/setup-python` to a full commit SHA
  instead of a mutable tag, and added a second job running `pip-audit`
  against `requirements.txt` so dependency vulnerabilities get caught
  automatically going forward instead of only during a manual audit.

### Accepted risk, documented rather than "fixed"

- **Rate limiting is keyed on the direct socket peer address**
  (`get_remote_address` in `app/main.py`). Behind a reverse proxy or load
  balancer, every request would appear to come from the proxy's IP,
  collapsing all clients into one rate-limit bucket. I did not add
  blind `X-Forwarded-For` trust to fix this, because trusting that header
  without knowing the real proxy's IP would let any client spoof their
  address and bypass the limiter entirely, a worse problem than the one
  it would fix. If this is ever deployed behind a proxy: run Uvicorn with
  `--proxy-headers --forwarded-allow-ips=<proxy IP>` so only that specific,
  trusted proxy's forwarded header is honored. The current bare
  `docker run -p 8000:8000` deployment described in the README is not
  affected, since there's no proxy in front of it.
- **`starlette==0.37.2` is pinned below the version I'd otherwise default
  to**, because `fastapi==0.111.0` hard-requires `starlette<0.38.0,>=0.37.2`
  (confirmed via the installed package's own metadata) — this pin is what
  broke the app once already when `prometheus-fastapi-instrumentator`
  pulled in a newer Starlette (see ADR-0011). A Starlette advisory around
  unbounded multipart/form-data parsing was raised during the audit, but
  this service has no file-upload or form-data endpoints at all (confirmed
  by grepping for `UploadFile`/`File(`/`Form(`/`multipart` across the
  codebase, zero matches), so the vulnerable code path is never reached
  here regardless of the pinned version. Upgrading both `fastapi` and
  `starlette` together is possible but riskier than the actual exposure
  warrants right now; `pip-audit` running in CI (see above) will flag it
  automatically if that changes.
- **No API-key layer on `/sentiment`/`/sentiment/batch`**, only per-IP rate
  limiting (ADR-0007). This is intentional and matches the challenge's
  requirement for a public HTTP endpoint; it's called out here so it's a
  conscious trade-off, not an oversight, if this code is ever reused
  outside the challenge context.

## Consequences

### Pros

- Closes every concretely exploitable or easily-fixed gap the audit found,
  at effectively zero cost to the app's behavior or scope.
- `pip-audit` in CI means dependency vulnerabilities get caught on every
  push, not just when someone remembers to run an audit by hand.
- The accepted-risk items are now written down with the actual reasoning,
  so a future reader (or judge) doesn't have to re-derive whether they were
  missed or deliberately left alone.

### Cons

- SHA-pinned GitHub Actions need manual bumping (or a Dependabot config)
  to pick up future action updates; they won't silently follow `v7` like
  a tag would.
- The reverse-proxy rate-limiting gap is still a real limitation for
  anyone who deploys this behind a proxy without following the
  `--forwarded-allow-ips` guidance above.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Trust `X-Forwarded-For` unconditionally to fix rate limiting behind a proxy** | Makes IP spoofing trivial for any direct client; worse than the problem it solves without a specific trusted-proxy IP to anchor on. |
| **Force-upgrade `starlette`/`fastapi` immediately to sidestep the multipart advisory** | Already caused a real outage once in this project (ADR-0011); not worth the risk for a code path this service never exercises. `pip-audit` in CI is the safer long-term answer. |
