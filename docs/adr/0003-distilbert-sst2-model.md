# ADR-0003: Use DistilBERT fine-tuned on SST-2 as the classification model

- **Status:** Accepted
- **Date:** 2026-07-29
- **Author:** Ricardo Martinez B

## Context

Once the Hugging Face Inference API was chosen ([ADR-0002](0002-huggingface-inference-api.md)),
a specific model was needed. It had to output a binary sentiment label
compatible with commonly available labeled review datasets, and be reliably
hosted on the Inference API without long cold-start times.

## Decision

The model
[`distilbert/distilbert-base-uncased-finetuned-sst-2-english`](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english)
was selected, configurable via the `HF_MODEL` environment variable
(see [`app/config.py`](../../app/config.py)).

## Rationale

- It is one of the most widely used, well-documented sentiment models on the
  Hugging Face Hub, fine-tuned on SST-2 (Stanford Sentiment Treebank).
- It returns exactly two labels, `POSITIVE`/`NEGATIVE`, with a confidence
  score — matching the binary `label` column used in the IMDB dataset chosen
  for evaluation ([ADR-0005](0005-sample-dataset-instead-of-full-csv.md)).
- Being a distilled model, it is smaller and faster to serve than full BERT,
  reducing the chance of long "model loading" (`503`) responses from the
  Inference API.

## Consequences

### Pros

- No additional post-processing is needed to map model output to the
  API's `label`/`score` response fields.
- Swappable: any other Hugging Face text-classification model can be used by
  changing `HF_MODEL`, as long as it returns the same
  `[[{"label", "score"}, ...]]` response shape.

### Cons

- Binary POSITIVE/NEGATIVE output cannot express neutral sentiment; texts that
  are genuinely neutral will still be forced into one of the two classes.
- Trained primarily on movie-review-style English text; accuracy may be lower
  on domains very different from its training data (e.g. highly technical or
  non-English text).

## Alternatives considered

| Alternative | Reason not adopted |
|-------------|---------------------|
| **`cardiffnlp/twitter-roberta-base-sentiment`** (3-class: negative/neutral/positive) | Would have required a 3-label evaluation dataset and slightly more complex response parsing; the 2-class model matches the chosen dataset directly. |
| **Full `bert-base-uncased` fine-tuned variants** | Larger model, no measurable accuracy benefit for this use case, and higher risk of slow/",loading" responses on the free Inference API tier. |
