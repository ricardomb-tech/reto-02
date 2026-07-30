# Architecture Decision Records (ADR)

This directory collects the main architecture decisions made while building
this project. Each ADR documents the context a decision arose from, the
alternative that was chosen, and the consequences it had on the design of the
solution.

The goal is to leave a record of the reasoning behind decisions that would be
costly to change or that directly influence how the application behaves.

## ADR structure

All documents follow the same structure:

- **Status:** whether the decision is proposed, accepted, or superseded.
- **Context:** the problem or need that motivated the decision.
- **Decision:** the chosen solution and the reasons for adopting it.
- **Consequences:** a summary of the benefits, limitations, and trade-offs
  taken on.

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

## Why do these documents exist?

The README explains **what** the project does and how to run it. ADRs answer
a different question: **why was it built this way?**

This is where decisions such as the following are documented:

- why sentiment analysis was chosen over summarization or entity extraction;
- why the Hugging Face Inference API was chosen over OpenAI or a local model;
- why this specific DistilBERT/SST-2 model was chosen;
- why the solution is exposed as a FastAPI endpoint rather than a CLI script;
- why the repository ships a small original sample instead of the full
  Kaggle CSV;
- why caching is in-memory instead of an external store like Redis;
- why rate limiting is applied per client IP, with upstream backoff on top.

Keeping this history makes it easier to understand the project's evolution
and helps anyone follow the technical reasoning behind the solution without
having to reverse-engineer it from the source code.
