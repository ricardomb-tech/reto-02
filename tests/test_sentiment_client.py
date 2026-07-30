from unittest.mock import patch

from app.sentiment_client import _best_from_scores


def test_best_from_scores_clear_positive():
    scores = [{"label": "POSITIVE", "score": 0.98}, {"label": "NEGATIVE", "score": 0.02}]
    assert _best_from_scores(scores) == {"label": "POSITIVE", "score": 0.98}


def test_best_from_scores_clear_negative():
    scores = [{"label": "POSITIVE", "score": 0.05}, {"label": "NEGATIVE", "score": 0.95}]
    assert _best_from_scores(scores) == {"label": "NEGATIVE", "score": 0.95}


def test_best_from_scores_low_confidence_becomes_neutral():
    with patch("app.sentiment_client.settings.neutral_confidence_threshold", 0.6):
        scores = [{"label": "POSITIVE", "score": 0.52}, {"label": "NEGATIVE", "score": 0.48}]
        assert _best_from_scores(scores) == {"label": "NEUTRAL", "score": 0.52}


def test_best_from_scores_above_threshold_keeps_original_label():
    with patch("app.sentiment_client.settings.neutral_confidence_threshold", 0.6):
        scores = [{"label": "POSITIVE", "score": 0.61}, {"label": "NEGATIVE", "score": 0.39}]
        assert _best_from_scores(scores) == {"label": "POSITIVE", "score": 0.61}
