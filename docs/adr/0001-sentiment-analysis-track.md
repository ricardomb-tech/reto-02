# ADR-0001: Solve the challenge with sentiment analysis

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge ("Reto 2 - Dato que Piensa") lets you pick one of three
problems to solve with a real AI model: sentiment analysis, automatic
summarization, or entity extraction. Any of the three clears the base
requirements.

## Decision

I went with sentiment analysis.

## Rationale

- It maps onto **labeled, binary-classification datasets** (IMDB reviews,
  for example), so I can compute an objective, reproducible **accuracy
  metric** end to end (see [`scripts/evaluate.py`](../../scripts/evaluate.py))
  instead of eyeballing whether the output looks right.
- Summarization and entity extraction are harder to score without a human
  judge or a heavier metric (ROUGE, entity-level F1). That's extra scope for
  no extra confidence.
- Solid, pretrained sentiment models (DistilBERT/SST-2) are free on the
  Hugging Face Inference API, so the whole thing stays simple to build and
  free to run.

## Consequences

### Pros

- I can prove correctness with a single number, accuracy on a labeled
  sample, which a judge can check by just re-running `scripts/evaluate.py`.
- The output shape (`label` + `score`) is simple and stable, so error
  handling and testing stay simple too.

### Cons

- It's less flashy than summarization or NER. The capability on display is
  narrower.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Automatic summarization** | Hard to score objectively without a reference metric like ROUGE, or someone reading the output by hand. |
| **Entity extraction (NER)** | Needs an entity-labeled dataset and a more involved scoring setup (entity-level precision/recall) to prove it works. |
