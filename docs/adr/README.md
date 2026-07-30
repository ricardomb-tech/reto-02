# Architecture Decision Records (ADR)

This folder holds the decisions I made while building this project, and why
I made them. Each ADR covers the problem I was facing, what I chose to do
about it, and what that choice cost me or bought me.

I write these down for decisions that are expensive to reverse or that shape
how the app behaves day to day. Smaller stuff just lives in the code.

## ADR structure

Every document follows the same shape:

- **Status:** proposed, accepted, or superseded.
- **Context:** what problem pushed me toward a decision.
- **Decision:** what I picked, and why.
- **Consequences:** the trade-offs I'm living with as a result.

## Index

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-sentiment-analysis-track.md) | Solve the challenge with sentiment analysis | ✅ Accepted |
| [0002](0002-huggingface-inference-api.md) | Use the Hugging Face Inference API as the AI service | ✅ Accepted |
| [0003](0003-distilbert-sst2-model.md) | Use DistilBERT fine-tuned on SST-2 as the classification model | ✅ Accepted |
| [0004](0004-fastapi-rest-endpoint.md) | Expose the solution as a FastAPI REST endpoint | ✅ Accepted |
| [0005](0005-sample-dataset-instead-of-full-csv.md) | Ship a small original sample instead of the full IMDB CSV | ✅ Accepted |
| [0006](0006-in-memory-ttl-cache.md) | In-memory TTL cache for repeated requests (Bonus B) | ✅ Accepted |
| [0007](0007-per-ip-rate-limiting.md) | Per-IP rate limiting with slowapi, plus upstream backoff | ✅ Accepted |
| [0008](0008-async-http-client-and-batch-endpoint.md) | Async HTTP client and a batch endpoint for latency and throughput | ✅ Accepted |
| [0009](0009-neutral-confidence-threshold.md) | Confidence threshold for a NEUTRAL label | ✅ Accepted |
| [0010](0010-circuit-breaker-for-upstream-resilience.md) | In-process circuit breaker for upstream resilience | ✅ Accepted |
| [0011](0011-observability-metrics-and-structured-logging.md) | Observability: Prometheus metrics and structured logging | ✅ Accepted |
| [0012](0012-pluggable-cache-backend.md) | Pluggable cache backend (in-memory default, optional Redis) | ✅ Accepted |
| [0013](0013-security-audit-hardening.md) | Security hardening from an internal audit | ✅ Accepted |

## Why bother with this?

The main README tells you what the project does and how to run it. These
documents answer a different question: why does it work this way instead of
some other way?

That covers things like:

- why sentiment analysis, and not summarization or entity extraction
- why Hugging Face's Inference API instead of OpenAI or a model running locally
- why this specific DistilBERT/SST-2 checkpoint
- why FastAPI instead of a CLI script
- why a small hand-written sample instead of the full Kaggle CSV
- why the cache lives in memory instead of something like Redis
- why rate limiting is per client IP, with retries on top of that

None of it is required reading to run the app. It's here so that later,
whoever picks this up (probably me, in a few months, having forgotten
everything) doesn't have to reverse-engineer the reasoning from the source
code.
