# ADR-0015: Data-driven NEUTRAL_CONFIDENCE_THRESHOLD calibration

- **Status:** Accepted (supersedes [ADR-0009](0009-neutral-confidence-threshold.md))
- **Date:** 2026-07-30
- **Author:** Ricardo Martinez B

## Context

ADR-0009 introduced `NEUTRAL_CONFIDENCE_THRESHOLD` with a default of `0.6`, picked
without measurement, to force NEUTRAL out of a binary model's low-confidence calls.
[ADR-0014](0014-native-3-class-sentiment-model.md) replaced that binary model with one
that predicts NEUTRAL natively, which changes the threshold's job: it's no longer the
only source of NEUTRAL, just a secondary gate for calls the model itself wasn't
confident about (whatever label won).

## Decision

- `_best_from_scores` in [`app/sentiment_client.py`](../../app/sentiment_client.py) now
  only applies the threshold when the winning label **isn't already** NEUTRAL — native
  NEUTRAL predictions pass through untouched.
- Built [`scripts/calibrate_threshold.py`](../../scripts/calibrate_threshold.py): it
  fetches the raw per-class scores once per row from Hugging Face directly (bypassing
  the running API and the threshold entirely), then replays the same gate logic locally
  for a range of candidate thresholds — one API call per row, not per
  (row, threshold) pair — reporting accuracy and macro-F1 for each via
  [`scripts/metrics_report.py`](../../scripts/metrics_report.py).
- Ran it against the 30-row labeled set (10 POSITIVE / 10 NEGATIVE / 10 NEUTRAL, see
  ADR-0014) with the live API and a real token, and set the new default to
  `NEUTRAL_CONFIDENCE_THRESHOLD=0.7` — the middle of the plateau that measured best,
  rather than the previous unmeasured `0.6` or the extreme edge of the sweep (see
  "A false start" below for why the edge was rejected).

## Measured results

| threshold | accuracy | macro-F1 |
|-----------|:--------:|:--------:|
| 0.35 – 0.40 | 83.3% | 0.815 |
| 0.45 | 86.7% | 0.857 |
| 0.50 | 83.3% | 0.825 |
| 0.55 – 0.60 *(old default range)* | 86.7% | 0.862 |
| **0.65 – 0.75 *(new default: 0.70, plateau midpoint)*** | **90.0%** | **0.898** |
| 0.80 | 86.7% | 0.865 |
| 0.85 | 83.3% | 0.828 |
| 0.90 | 80.0% | 0.780 |

Confusion matrix at threshold `0.70`:

```
expected \ predicted  POSITIVE   NEGATIVE   NEUTRAL
POSITIVE              10         0          0
NEGATIVE              0          9          1
NEUTRAL                1         1          8
```

## Rationale

- The curve rises to a genuine plateau around 0.65–0.75 and falls again past ~0.80, as
  the gate starts swallowing genuinely confident POSITIVE/NEGATIVE calls into NEUTRAL —
  the standard precision/recall tradeoff of a single global cutoff. Picking the
  plateau's **midpoint** rather than its edge is deliberate, for robustness against
  noise in a 30-row sample.
- **A false start, kept here because it's instructive:** the first calibration run
  looked like it wanted a threshold near `1.0` (accuracy climbing monotonically as the
  threshold rose). That run turned out to be hitting the *old* binary DistilBERT model
  because a local `.env` had `HF_MODEL` pinned explicitly, silently overriding the new
  code default. A monotonic "higher is always better" curve on a 30-row set is a red
  flag for overfitting to that specific sample — in production, real text rarely scores
  >99% confidence, so a threshold that high would push nearly everything to NEUTRAL.
  After fixing the stale override and re-running against the real 3-class model, the
  curve became the non-monotonic one above, with a genuine interior maximum — a much
  more trustworthy signal, and the one this decision is actually based on.
- The gate demonstrably helps when the model itself is unsure: a mixed-signal review
  ("The special effects were impressive but the story dragged on forever.", labeled
  NEGATIVE) scores only 0.46 on `negative` — genuinely uncertain, and the gate catches
  it. It does **not** help when the model is confidently wrong: "It was okay, nothing I
  would rush to recommend..." (labeled NEUTRAL) scores 0.87 on `positive` — no threshold
  below 1.0 fixes a confidently wrong call, only a genuinely uncertain one. That's a
  ceiling on this approach, not a bug in the calibration.

## Consequences

### Pros

- The default is backed by a reproducible measurement instead of a guess, and
  `scripts/calibrate_threshold.py` is reusable whenever the model, dataset, or domain
  changes.
- Calibration stays cheap regardless of how many thresholds are swept: one API call per
  row, since the raw scores are fetched once and reused for every candidate threshold.

### Cons

- 30 rows (10 per class) is still a small validation set; a larger or more realistic
  sample (e.g. pulling more rows from the real Kaggle IMDB dataset per
  [ADR-0005](0005-sample-dataset-instead-of-full-csv.md)) could shift the optimum.
- Still a single global cutoff — the same blunt-instrument caveat ADR-0009 already
  flagged. It cannot correct a confidently wrong native prediction, only an uncertain
  one.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Keep the unmeasured `0.6` default** | Measurably worse on this dataset (86.7% vs. 90.0% accuracy) and no way to know without calibrating. |
| **Drop the threshold now that the model predicts NEUTRAL natively** | Loses a demonstrated safety net for genuinely uncertain calls (the 0.46-confidence example above). |
| **Per-class thresholds instead of one global cutoff** | More parameters to tune on an already-small (30-row) calibration set; not worth the added complexity yet. |
