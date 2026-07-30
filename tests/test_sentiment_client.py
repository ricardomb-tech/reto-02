from unittest.mock import patch

from app.sentiment_client import _best_from_scores, _parse_batch_result


def test_best_from_scores_clear_positive():
    # cardiffnlp/twitter-roberta-base-sentiment-latest returns lowercase labels.
    scores = [
        {"label": "positive", "score": 0.90},
        {"label": "neutral", "score": 0.08},
        {"label": "negative", "score": 0.02},
    ]
    assert _best_from_scores(scores) == {"label": "POSITIVE", "score": 0.9}


def test_best_from_scores_clear_negative():
    scores = [
        {"label": "positive", "score": 0.03},
        {"label": "neutral", "score": 0.07},
        {"label": "negative", "score": 0.90},
    ]
    assert _best_from_scores(scores) == {"label": "NEGATIVE", "score": 0.9}


def test_best_from_scores_native_neutral_kept_as_is():
    scores = [
        {"label": "positive", "score": 0.20},
        {"label": "neutral", "score": 0.70},
        {"label": "negative", "score": 0.10},
    ]
    assert _best_from_scores(scores) == {"label": "NEUTRAL", "score": 0.7}


def test_best_from_scores_low_confidence_becomes_neutral():
    with patch("app.sentiment_client.settings.neutral_confidence_threshold", 0.6):
        scores = [
            {"label": "positive", "score": 0.40},
            {"label": "neutral", "score": 0.35},
            {"label": "negative", "score": 0.25},
        ]
        assert _best_from_scores(scores) == {"label": "NEUTRAL", "score": 0.4}


def test_best_from_scores_above_threshold_keeps_original_label():
    with patch("app.sentiment_client.settings.neutral_confidence_threshold", 0.6):
        scores = [
            {"label": "positive", "score": 0.61},
            {"label": "neutral", "score": 0.24},
            {"label": "negative", "score": 0.15},
        ]
        assert _best_from_scores(scores) == {"label": "POSITIVE", "score": 0.61}


def test_best_from_scores_low_confidence_neutral_stays_neutral():
    with patch("app.sentiment_client.settings.neutral_confidence_threshold", 0.6):
        scores = [
            {"label": "positive", "score": 0.10},
            {"label": "neutral", "score": 0.50},
            {"label": "negative", "score": 0.40},
        ]
        assert _best_from_scores(scores) == {"label": "NEUTRAL", "score": 0.5}


def test_parse_batch_result_one_score_list_per_text():
    # Shape returned by some models: one full per-class list per input text.
    payload = [
        [{"label": "positive", "score": 0.9}, {"label": "negative", "score": 0.1}],
        [{"label": "negative", "score": 0.8}, {"label": "positive", "score": 0.2}],
    ]
    assert _parse_batch_result(payload, expected_count=2) == [
        {"label": "POSITIVE", "score": 0.9},
        {"label": "NEGATIVE", "score": 0.8},
    ]


def test_parse_batch_result_flat_wrapped_in_one_outer_list():
    # Shape observed from cardiffnlp/twitter-roberta-base-sentiment-latest for list inputs:
    # a single outer list containing one winner dict (no runner-up classes) per input text.
    payload = [[{"label": "positive", "score": 0.9}, {"label": "negative", "score": 0.8}]]
    assert _parse_batch_result(payload, expected_count=2) == [
        {"label": "POSITIVE", "score": 0.9},
        {"label": "NEGATIVE", "score": 0.8},
    ]


def test_parse_batch_result_unexpected_shape_raises():
    from app.sentiment_client import SentimentServiceError

    payload = [{"label": "positive", "score": 0.9}, {"label": "negative", "score": 0.8}, {"label": "x", "score": 0.1}]
    try:
        _parse_batch_result(payload, expected_count=2)
        assert False, "expected SentimentServiceError"
    except SentimentServiceError:
        pass
