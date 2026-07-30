"""Calibrate NEUTRAL_CONFIDENCE_THRESHOLD against a labeled CSV using real model scores.

Unlike scripts/evaluate.py, this does not go through the running FastAPI service — it
calls the Hugging Face Inference API directly once per row, capturing the full per-class
score list, then replays app.sentiment_client's NEUTRAL-gate decision locally for a range
of candidate thresholds. That means calibration costs one API call per row, not one call
per (row, threshold) pair.

For each candidate threshold it reports accuracy and macro-F1 (see scripts/metrics_report.py),
and recommends the threshold with the best macro-F1 (ties broken by accuracy, then by the
higher threshold, since a higher threshold is the more conservative choice about NEUTRAL).

Usage:
    python scripts/calibrate_threshold.py --csv data/sample_reviews.csv
    python scripts/calibrate_threshold.py --thresholds 0.4,0.45,0.5,0.55,0.6,0.65,0.7
"""
import argparse
import csv
import os
import sys

import requests
from dotenv import load_dotenv

from metrics_report import classification_report

load_dotenv()

LABELS = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
HF_MODEL = os.getenv("HF_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))


def _fetch_raw_scores(rows: list) -> list:
    """Call Hugging Face once per row and return the raw per-class score list for each."""
    token = os.getenv("HF_API_TOKEN")
    if not token:
        print("HF_API_TOKEN is not set; cannot call the model directly.", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    raw_scores = []
    for i, row in enumerate(rows, start=1):
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": row["text"], "options": {"wait_for_model": True}},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        raw_scores.append(response.json()[0])
        print(f"[{i}/{len(rows)}] fetched scores for: {row['text'][:60]!r}", file=sys.stderr)
    return raw_scores


def _label_at_threshold(scores: list, threshold: float) -> str:
    """Mirror app.sentiment_client._best_from_scores's decision, for a given threshold."""
    best = max(scores, key=lambda item: item["score"])
    label = str(best["label"]).strip().upper()
    score = float(best["score"])
    if label != "NEUTRAL" and score < threshold:
        label = "NEUTRAL"
    return label


def calibrate(csv_path: str, thresholds: list) -> None:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    raw_scores = _fetch_raw_scores(rows)
    expected = [row["label"].strip().upper() for row in rows]

    best = None
    print(f"\n{'threshold':>9}  {'accuracy':>8}  {'macro-F1':>8}")
    for threshold in thresholds:
        predicted = [_label_at_threshold(scores, threshold) for scores in raw_scores]
        report = classification_report(expected, predicted, LABELS)
        print(f"{threshold:>9.2f}  {report.accuracy * 100:>7.1f}%  {report.macro_f1:>8.3f}")

        key = (report.macro_f1, report.accuracy, threshold)
        if best is None or key > best[0]:
            best = (key, threshold, report)

    _, best_threshold, best_report = best
    print(f"\nRecommended NEUTRAL_CONFIDENCE_THRESHOLD = {best_threshold:.2f}")
    print(f"(accuracy {best_report.accuracy * 100:.1f}%, macro-F1 {best_report.macro_f1:.3f})\n")
    print(best_report.render())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate NEUTRAL_CONFIDENCE_THRESHOLD against labeled data.")
    parser.add_argument("--csv", default="data/sample_reviews.csv", help="Path to labeled CSV file.")
    parser.add_argument(
        "--thresholds",
        default="0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75",
        help="Comma-separated candidate thresholds to try.",
    )
    args = parser.parse_args()
    calibrate(args.csv, [float(t) for t in args.thresholds.split(",")])
