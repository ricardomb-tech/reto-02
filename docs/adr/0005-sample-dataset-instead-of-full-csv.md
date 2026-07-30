# ADR-0005: Ship a small original sample instead of the full IMDB CSV

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge requires a public dataset, documented in the README with a
link to the source. The one I picked,
[IMDB Dataset of 50K Movie Reviews](https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews)
(Kaggle), is about 65 MB of third-party, user-generated review text. The
challenge also says the repository shouldn't include extra attachments
beyond source code, README, and `requirements.txt`.

## Decision

I did **not** commit the full IMDB CSV. Instead,
[`data/sample_reviews.csv`](../../data/sample_reviews.csv) holds 20 short,
original reviews I wrote myself for this project, using the same
`text,label` schema. [`scripts/evaluate.py`](../../scripts/evaluate.py) runs
against it to show end-to-end accuracy against the live API. The README
explains how to reproduce results against the real Kaggle CSV by pointing
`scripts/evaluate.py --csv` at it instead.

## Rationale

- Committing a 65 MB third-party dataset would bloat the repo and blur the
  "no extra attachments" line, even though that rule is really about the
  email delivery, not the repo's file count.
- The original dataset is user-generated content redistributed under
  Kaggle's terms. Writing a small, clearly original sample sidesteps any
  licensing question while still exercising the same code path,
  `scripts/evaluate.py` calling the live `/sentiment` endpoint.
- 20 rows is enough for a meaningful, reproducible accuracy number a judge
  can re-run in seconds, without waiting on 50,000 HTTP calls against a
  rate-limited free API.

## Consequences

### Pros

- The repo stays small and clones fast.
- No copyright or redistribution concerns in what's committed.
- The evaluation still proves the same thing end to end: a real API call, a
  real label, a real accuracy score (20/20, 100% observed, see the
  README/resumen).

### Cons

- 20 samples is a much thinner accuracy signal than the full 50K dataset
  would give.
- Anyone wanting to validate against the full dataset has to download it
  from Kaggle separately.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Commit the full 50K-row CSV** | Adds ~65 MB of third-party content for no benefit beyond what a small sample already shows. |
| **Commit a random subsample of the real CSV (e.g. 200 rows)** | Still redistributes third-party review text and needs downloading/filtering the source file as a build step. An original sample sidesteps the licensing question entirely. |
