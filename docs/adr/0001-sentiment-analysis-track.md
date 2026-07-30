# ADR-0001: Solve the challenge with sentiment analysis

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge ("Reto 2 — Dato que Piensa") allows solving one of three problems
with a real AI model: sentiment analysis, automatic summarization, or entity
extraction. Any of the three would satisfy the base requirements.

## Decision

Sentiment analysis was chosen as the track to implement.

## Rationale

- It maps naturally onto **labeled, binary-classification datasets** (e.g. IMDB
  reviews), which makes it possible to compute an objective, reproducible
  **accuracy metric** end-to-end (see [`scripts/evaluate.py`](../../scripts/evaluate.py)).
- Summarization and entity extraction are harder to score objectively without a
  human judge or a more complex metric (ROUGE, entity-level F1), which adds
  scope without adding confidence for an evaluator.
- Pretrained, well-known models for sentiment classification (DistilBERT/SST-2)
  are freely available on the Hugging Face Inference API, keeping the solution
  simple and free to run.

## Consequences

### Pros

- The solution can prove correctness with a single number (accuracy on a
  labeled sample), which is easy for a judge to verify by re-running
  `scripts/evaluate.py`.
- The output shape (`label` + `score`) is simple and stable, simplifying error
  handling and testing.

### Cons

- Less "creative" than summarization or NER; the demonstrated capability is
  narrower.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Automatic summarization** | Harder to evaluate objectively without a reference-based metric (ROUGE) or manual review. |
| **Entity extraction (NER)** | Requires an entity-labeled dataset and a more involved scoring approach (entity-level precision/recall) to demonstrate correctness. |
