# ADR-0003: Use DistilBERT fine-tuned on SST-2 as the classification model

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

With the Hugging Face Inference API already chosen
([ADR-0002](0002-huggingface-inference-api.md)), I still needed a specific
model. It had to output a binary sentiment label that matched common labeled
review datasets, and stay reliably hosted on the Inference API without long
cold starts.

## Decision

I picked
[`distilbert/distilbert-base-uncased-finetuned-sst-2-english`](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english),
configurable through the `HF_MODEL` environment variable (see
[`app/config.py`](../../app/config.py)).

## Rationale

- It's one of the most widely used, well-documented sentiment models on the
  Hub, fine-tuned on SST-2 (Stanford Sentiment Treebank).
- It returns exactly two labels, `POSITIVE`/`NEGATIVE`, with a confidence
  score, which lines up with the binary `label` column in the IMDB dataset I
  use for evaluation ([ADR-0005](0005-sample-dataset-instead-of-full-csv.md)).
- Being distilled, it's smaller and faster to serve than full BERT, which
  cuts the odds of a long "model loading" (`503`) response from the
  Inference API.

## Consequences

### Pros

- No extra post-processing to map model output onto the API's `label`/`score`
  fields.
- Swappable: any other Hugging Face text-classification model works if I
  change `HF_MODEL`, as long as it returns the same
  `[[{"label", "score"}, ...]]` shape.

### Cons

- Binary POSITIVE/NEGATIVE can't express neutral sentiment. Genuinely
  neutral text still gets forced into one of the two buckets.
- It's trained mostly on movie-review-style English, so accuracy can drop on
  very different domains, technical text or non-English input, for example.

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **`cardiffnlp/twitter-roberta-base-sentiment`** (3-class: negative/neutral/positive) | Would need a 3-label evaluation dataset and slightly more parsing; the 2-class model matches the dataset I already have. |
| **Full `bert-base-uncased` fine-tuned variants** | Bigger model, no real accuracy gain for this use case, and more likely to sit "loading" on the free Inference API tier. |
