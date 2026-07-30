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
  `Content-Security-Policy` restricting scripts/styles to `'self'`.

  **Update, found via a real-browser test (not just `curl`):** the CSP's
  `script-src 'self'` silently blocked the demo page's own inline
  `<script>` block — `'self'` only covers same-origin *external* scripts,
  not inline ones, so every browser enforcing the policy ran zero
  JavaScript on `/demo` and the "Analyze" button did nothing. Nothing
  caught this earlier because prior verification only checked the JSON API
  responses with `curl`, never loaded the page in an actual browser with
  CSP enforcement on. Fixed by moving the script out to
  [`static/app.js`](../../static/app.js), loaded via
  `<script src="app.js">` — same-origin external scripts are allowed under
  `script-src 'self'`, so the policy stays exactly as strict as intended
  instead of adding `'unsafe-inline'` (which would have defeated most of
  the point of setting a CSP here at all). Verified with a headless
  Playwright browser against the live CSP-enforcing response: clicking
  Analyze now fires the `/sentiment` request and renders the result.
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

  **Update, 2026-07-30 — the `pip-audit` job did exactly what it was
  added for:** it (via GitHub's Dependabot, reading the same
  `requirements.txt`) opened 7 alerts against the pinned `starlette==0.37.2`
  (DoS via multipart parsing, DoS via unbounded form limits, missing Host
  header validation poisoning `request.url.path`, SSRF/NTLM credential
  theft via UNC paths in `StaticFiles` on Windows — relevant here, this
  project's own `/demo` route uses `StaticFiles` — arbitrary HTTP method
  dispatch via `getattr` on `HTTPEndpoint`, and unvalidated path
  concatenation poisoning `request.url.hostname`). Dependabot's own
  auto-fix PR only bumped `starlette` to `1.3.1` in isolation, which is
  unsatisfiable — `fastapi==0.111.0` hard-requires `starlette<0.38.0`, so
  both the `pip-audit` job and the `pytest` job failed on that PR ("Cannot
  install ... because these package versions have conflicting
  dependencies"). Fixing it for real meant upgrading the whole chain, not
  just the one flagged package: `fastapi` 0.111.0 → 0.141.1 (requires
  `pydantic>=2.9.0`, so `pydantic` 2.7.4 → 2.13.4 came with it), `starlette`
  0.37.2 → 1.3.1, and `prometheus-fastapi-instrumentator` 7.1.0 → 8.1.0
  (7.x hard-caps `starlette<1.0.0`; this is the exact same package that
  caused a real outage the last time its Starlette pin moved, see
  ADR-0011, so it got the most scrutiny here). Verified before trusting it:
  a clean venv install of the new `requirements.txt` from scratch (mirroring
  what CI actually runs, not just patching the existing dev venv), the full
  `pytest` suite green in that clean venv, `pip-audit -r requirements.txt`
  reporting no known vulnerabilities, and a live smoke test of every route
  (`/health`, `/sentiment`, `/sentiment/batch`, `/metrics`, `/demo/`,
  `/demo/app.js`, `/docs`, the 400/413 error paths, and that the security
  headers/CSP from this same ADR are still present on responses) against a
  freshly started server on the new dependency set.

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
- ~~`starlette==0.37.2` is pinned below the version I'd otherwise default to~~
  — **resolved, see the 2026-07-30 update below.** This bullet originally
  argued the pin was safe because the only known advisory at the time
  (unbounded multipart parsing) didn't apply to a service with no
  file-upload endpoints. That stopped being the full picture once GitHub
  opened 7 Dependabot alerts against `starlette` (see below), so the
  pin was actually upgraded rather than re-argued around.
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
