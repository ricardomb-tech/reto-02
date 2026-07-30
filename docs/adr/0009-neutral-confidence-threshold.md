# ADR-0009: Confidence threshold for a NEUTRAL label

- **Status:** Accepted
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

ADR-0003 already flagged this as a known limitation: DistilBERT/SST-2 only
returns `POSITIVE` or `NEGATIVE`, so genuinely ambiguous or lukewarm text
gets forced into one of the two buckets. Binary softmax confidence is
mathematically always at least 0.5 for whichever label wins, so a "0.51"
result is really the model shrugging, not a real signal.

## Decision

`_best_from_scores` in [`app/sentiment_client.py`](../../app/sentiment_client.py)
now downgrades the label to `"NEUTRAL"` whenever the winning score falls
below `settings.neutral_confidence_threshold`, configurable via
`NEUTRAL_CONFIDENCE_THRESHOLD` (default `0.6`).

## Rationale

- It directly answers a limitation I already wrote down in ADR-0003,
  instead of leaving it as a documented "known issue" forever.
- The threshold is a single float comparison on data I already have.
  No new model, no new API call, no extra latency.
- Defaulting to `0.6` is conservative: it only reclassifies calls the
  model itself wasn't confident about, so it doesn't change the label on
  anything clear-cut.

## Consequences

### Pros

- `data/sample_reviews.csv` is made of clear-cut reviews, so the existing
  20/20 accuracy result in `scripts/evaluate.py` is unaffected by the
  default threshold, verified by re-running the evaluation script.
- `NEUTRAL` is a real signal now, instead of an artificially confident
  POSITIVE or NEGATIVE on a coin-flip.

### Cons

- `scripts/evaluate.py`'s accuracy check only knows about POSITIVE/NEGATIVE
  labels; a CSV with genuinely neutral, labeled rows would need updated
  evaluation logic to score NEUTRAL correctly, since that's not something
  the original IMDB-style binary schema anticipates.
- The threshold is a blunt instrument: a single global cutoff, not
  calibrated per domain.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Leave it binary, document it as a known limitation** | That's what ADR-0003 already did; this ADR exists specifically to close that gap. |
| **Switch to a 3-class model (e.g. `cardiffnlp/twitter-roberta-base-sentiment`)** | Already rejected in ADR-0003's alternatives: needs a 3-label dataset and more parsing, for a problem a simple threshold on the existing model already solves well enough. |
