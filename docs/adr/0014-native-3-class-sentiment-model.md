# ADR-0014: Switch to a native 3-class sentiment model

- **Status:** Accepted (supersedes [ADR-0003](0003-distilbert-sst2-model.md))
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

ADR-0003 picked DistilBERT/SST-2, a binary POSITIVE/NEGATIVE model, and explicitly
rejected `cardiffnlp/twitter-roberta-base-sentiment` at the time because it "would need a
3-label evaluation dataset and slightly more parsing." ADR-0009 then papered over the
missing NEUTRAL class with a confidence threshold on top of the binary model, for the
same reason: no 3-label dataset to evaluate a 3-class model against.

That constraint no longer holds. [`data/sample_reviews.csv`](../../data/sample_reviews.csv)
now includes 10 genuinely NEUTRAL-labeled rows alongside the original 10
POSITIVE/10 NEGATIVE (30 total), specifically so a 3-class model's NEUTRAL predictions
can be measured, not just assumed.

## Decision

`HF_MODEL` now defaults to
[`cardiffnlp/twitter-roberta-base-sentiment-latest`](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest),
a RoBERTa model fine-tuned on ~124M tweets that natively returns `positive`/`neutral`/`negative`
with a score per class, instead of DistilBERT/SST-2's binary output.

## Rationale

- NEUTRAL is now a real model decision, not an artifact inferred from low binary
  confidence (that inference still exists as a secondary safety net — see
  [ADR-0015](0015-data-driven-neutral-threshold.md) — but it's no longer the *only*
  source of NEUTRAL).
- Actively maintained, widely used checkpoint on the Hub, same general shape of output
  (`{"label", "score"}` dicts) as the previous model, so most of
  [`app/sentiment_client.py`](../../app/sentiment_client.py)'s parsing carried over
  unchanged — see the batch-endpoint gotcha below for the one place it didn't.
- Measured end-to-end against the running API (not assumed): **90.0% accuracy, macro-F1
  0.898** on the 30-row labeled set, combined with the recalibrated threshold from
  ADR-0015. Full confusion matrix and per-class precision/recall in ADR-0015.

## Consequences

### Pros

- Real per-class metrics instead of a single accuracy number that couldn't say anything
  about NEUTRAL, since the old dataset had no NEUTRAL rows to check against.
- `scripts/evaluate.py` and `scripts/calibrate_threshold.py` (new, see ADR-0015) both
  report a confusion matrix and per-class precision/recall/F1 via
  [`scripts/metrics_report.py`](../../scripts/metrics_report.py), so future model swaps
  get the same rigor for free.

### Cons

- **Batch response shape gotcha (found via live testing, not assumed):** the Hugging
  Face Inference API returns a *different* payload shape for `/sentiment/batch`'s
  list-of-texts request than for a single-text request, for this specific model. A
  single text returns `[[{label,score} x 3 classes]]`. A list of N texts returns
  `[[{label,score} x N texts]]` — one flattened list wrapping N single "winner" dicts
  (top prediction only, no runner-up classes), not N per-text lists of 3 scores. The old
  `_parse_batch_result` assumed the latter shape unconditionally (true for DistilBERT),
  so on the new model it silently collapsed a 30-text batch down to a single result and
  crashed the endpoint with a 500 on the 29 texts left unfilled. Fixed by having
  `_parse_batch_result` detect which shape actually matches the number of texts sent
  (`len(payload) == expected_count` vs. `payload == [[... expected_count entries ...]]`),
  and making `_best_from_scores` accept either a list of class candidates or a single
  winner dict. Covered by
  `test_parse_batch_result_one_score_list_per_text` and
  `test_parse_batch_result_flat_wrapped_in_one_outer_list` in
  [`tests/test_sentiment_client.py`](../../tests/test_sentiment_client.py).
- Domain shift: tuned on tweets, not movie reviews — but it measured well on this
  review-style test set regardless (numbers above), so this stayed a documented risk
  rather than a blocker.
- Confidently-wrong NEUTRAL calls are still the model's weak spot: factual/descriptive
  sentences ("the cast includes...", "the film runs about two hours...") are tagged
  NEUTRAL with high confidence, but genuinely mixed-opinion text ("not the best, not the
  worst") often gets pulled toward POSITIVE/NEGATIVE with *high* confidence too — no
  threshold can fix a confidently wrong call, only a genuinely uncertain one (see
  ADR-0015).

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Stay on DistilBERT/SST-2 + threshold only** | Tops out lower on measured accuracy/macro-F1 than the native 3-class model + recalibrated threshold (see ADR-0015's numbers); the earlier objection (no 3-label dataset) no longer applies now that the dataset has NEUTRAL rows. |
| **`cardiffnlp/twitter-roberta-base-sentiment`** (older, non-`-latest`) | Returns generic `LABEL_0`/`LABEL_1`/`LABEL_2` instead of named labels, requiring a manually maintained id-to-label map. |
| **A movie-review-specific 3-class model** | No well-maintained, widely used Hub checkpoint fine-tuned on movie reviews with 3 classes was found; `cardiffnlp`'s is the standard off-the-shelf option and measured well enough on this domain. |
