# ADR-0005: Ship a small original sample instead of the full IMDB CSV

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

The challenge requires using a public dataset and documenting it in the
README with a link to the source. The chosen dataset,
[IMDB Dataset of 50K Movie Reviews](https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews)
(Kaggle), is ~65 MB and contains third-party, user-generated review text. The
challenge also states the repository must not include extra attachments
beyond source code, README, and `requirements.txt`.

## Decision

The full IMDB CSV is **not** committed to the repository. Instead,
[`data/sample_reviews.csv`](../../data/sample_reviews.csv) contains 20 short,
original example reviews (written for this project) using the same
`text,label` schema, used by [`scripts/evaluate.py`](../../scripts/evaluate.py)
to demonstrate end-to-end accuracy against the live API. The README documents
how to reproduce results against the real Kaggle CSV by pointing
`scripts/evaluate.py --csv` at it.

## Rationale

- Committing a 65 MB third-party dataset would bloat the repository and blur
  the line with "no additional attachments," even though the requirement is
  really about the email delivery, not the repo's internal file count.
- The review text in the original dataset is user-generated content
  redistributed under Kaggle's terms; recreating a small, clearly original
  sample avoids any licensing ambiguity while still exercising the exact same
  code path (`scripts/evaluate.py` calling the live `/sentiment` endpoint).
- A 20-row sample is enough to produce a meaningful, reproducible accuracy
  number a judge can re-run in seconds, without waiting on 50,000 HTTP calls
  against a rate-limited free API.

## Consequences

### Pros

- Repository stays small and fast to clone.
- No copyright/redistribution concerns for the committed data.
- Evaluation still proves the same thing end-to-end: real API call, real
  label, real accuracy score (20/20 = 100% observed, see the resumen/README).

### Cons

- 20 samples is a much smaller and less statistically robust accuracy signal
  than evaluating on the full 50K dataset.
- A judge wanting to validate against the full dataset must download it
  separately from Kaggle.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **Commit the full 50K-row CSV** | Adds ~65 MB of third-party content to the repo for no benefit beyond what a small sample already demonstrates. |
| **Commit a random subsample of the real CSV (e.g. 200 rows)** | Still redistributes third-party review text and requires downloading/filtering the source file as a build step; an original sample avoids the licensing question entirely. |
