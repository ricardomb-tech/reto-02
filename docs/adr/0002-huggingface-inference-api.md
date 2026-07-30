# ADR-0002: Use the Hugging Face Inference API as the AI service

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge offers three options for the AI backend: the Hugging Face
Inference API, the OpenAI API, or a local model run through Transformers.
Whatever I picked had to be reachable with a simple HTTP call, keyed by an
environment-variable secret, and usable without paying for anything.

## Decision

I went with the **Hugging Face Inference API**, called over HTTPS from
[`app/sentiment_client.py`](../../app/sentiment_client.py).

## Rationale

- It's free with a personal access token (read scope), no credit card
  involved. OpenAI, by contrast, wants billing set up before you send a
  single request.
- It fits the "API key via environment variable" requirement directly: one
  `HF_API_TOKEN`, read through `python-dotenv` (see
  [`app/config.py`](../../app/config.py)).
- It skips bundling a multi-hundred-MB model file plus the `transformers`
  and `torch` dependency chain that a local approach would need. That keeps
  the container image and cold-start time small.

## Consequences

### Pros

- No local compute or GPU needed. The service just needs a network
  connection and a token.
- Swapping models is a one-line env var change (`HF_MODEL`), not a code
  change.

### Cons

- It adds a network dependency: the API can be briefly unavailable, rate
  limited, or slow to wake up when a model hasn't been called in a while
  (`503`, "model is loading"). I handle this with retries and backoff in
  `sentiment_client.py`.
- Latency is higher than an in-process local model would give you.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **OpenAI API** | Needs a paid, billed account; there's no free tier that fits a judged coding challenge. |
| **Local model via Transformers** | Means bundling `torch` and `transformers` and downloading a multi-hundred-MB checkpoint. That makes the Docker image and setup a lot heavier for no real benefit at this scale. |
