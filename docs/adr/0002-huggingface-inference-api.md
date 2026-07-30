# ADR-0002: Use the Hugging Face Inference API as the AI service

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge allows three options for the AI backend: the Hugging Face
Inference API, the OpenAI API, or a local model run with Transformers. The
service needed to be reachable with a simple HTTP call, keyed by an
environment-variable secret, and usable without a paid plan.

## Decision

The **Hugging Face Inference API** was chosen as the AI service, called over
HTTPS from [`app/sentiment_client.py`](../../app/sentiment_client.py).

## Rationale

- It is free to use with a personal access token (read scope), with no credit
  card required — unlike the OpenAI API, which requires billing setup.
- It fits the "API key via environment variable" requirement directly: a single
  `HF_API_TOKEN` read through `python-dotenv` (see
  [`app/config.py`](../../app/config.py)).
- It avoids bundling a multi-hundred-MB model file and a heavy `transformers` +
  `torch` dependency chain, which a local-Transformers approach would require —
  keeping the container image and cold-start time small.

## Consequences

### Pros

- Zero local compute/GPU requirements; the service only needs an internet
  connection and a token.
- Model can be swapped via the `HF_MODEL` environment variable without code
  changes.

### Cons

- Adds a network dependency: the API can be temporarily unavailable, rate
  limited, or require warm-up time when a model has not been called recently
  (`503`, "model is loading"). This is handled explicitly with retries/backoff
  in `sentiment_client.py`.
- Latency is higher than an in-process local model would be.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **OpenAI API** | Requires a paid/billed account; no free tier suitable for a judged coding challenge. |
| **Local model via Transformers** | Would require bundling `torch` + `transformers` and downloading a multi-hundred-MB checkpoint, making the Docker image and setup significantly heavier for no added benefit at this scale. |
