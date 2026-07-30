"""Evaluate the running sentiment API against a labeled CSV dataset and report metrics.

Usage:
    python scripts/evaluate.py --csv data/sample_reviews.csv --url http://localhost:8000/sentiment

The CSV must have two columns: "text" and "label" (POSITIVE/NEGATIVE/NEUTRAL). Reports a
confusion matrix plus per-class precision/recall/F1 and overall accuracy/macro-F1, not just a
single accuracy number (see scripts/metrics_report.py).

Requests are paced to stay under the API's own rate limit (see RATE_LIMIT in app/config.py),
and any unexpected 429 is retried with backoff rather than counted as a hard failure.
"""
import argparse
import csv
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

from metrics_report import classification_report

load_dotenv()

LABELS = ["POSITIVE", "NEGATIVE", "NEUTRAL"]


def _seconds_between_requests(rate_limit: str) -> float:
    match = re.match(r"\s*(\d+)\s*/\s*(second|minute|hour|day)\s*", rate_limit, re.IGNORECASE)
    if not match:
        return 0.0
    count, period = match.groups()
    period_seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[period.lower()]
    return period_seconds / int(count)


def _post_with_retry(url: str, text: str, max_retries: int = 3):
    """POST to the API, backing off and retrying if this service's own rate limiter kicks in."""
    for attempt in range(1, max_retries + 1):
        response = requests.post(url, json={"text": text}, timeout=30)
        if response.status_code != 429:
            return response
        wait_seconds = int(response.headers.get("Retry-After", 60))
        print(f"[rate-limited] waiting {wait_seconds}s before retrying (attempt {attempt}/{max_retries})...", file=sys.stderr)
        time.sleep(wait_seconds)
    return response


def evaluate(csv_path: str, url: str) -> None:
    delay = _seconds_between_requests(os.getenv("RATE_LIMIT", "10/minute"))
    errors = 0
    first_request = True
    started_at = time.monotonic()
    expected_labels = []
    predicted_labels = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row["text"]
            expected_label = row["label"].strip().upper()

            if not first_request and delay:
                time.sleep(delay)
            first_request = False

            try:
                response = _post_with_retry(url, text)
                response.raise_for_status()
            except requests.exceptions.RequestException as exc:
                print(f"[error] request failed for text={text!r}: {exc}", file=sys.stderr)
                errors += 1
                continue

            predicted_label = response.json().get("label", "").upper()
            expected_labels.append(expected_label)
            predicted_labels.append(predicted_label)
            if predicted_label != expected_label:
                print(f"[mismatch] expected={expected_label} got={predicted_label} text={text!r}")

    elapsed = time.monotonic() - started_at
    print(f"\nEvaluated {len(expected_labels)} samples ({errors} request errors) in {elapsed:.2f}s (per-row mode).")
    print(classification_report(expected_labels, predicted_labels, LABELS).render())


def evaluate_batch(csv_path: str, url: str) -> None:
    """Same evaluation, but sends the whole CSV to /sentiment/batch in one call."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    batch_url = url.rsplit("/sentiment", 1)[0] + "/sentiment/batch"
    started_at = time.monotonic()
    response = requests.post(batch_url, json={"texts": [row["text"] for row in rows]}, timeout=60)
    response.raise_for_status()
    elapsed = time.monotonic() - started_at

    results = response.json()["results"]
    expected_labels = [row["label"].strip().upper() for row in rows]
    predicted_labels = [result["label"].upper() for result in results]

    print(f"\nEvaluated {len(rows)} samples in a single batch call, {elapsed:.2f}s (batch mode).")
    print(classification_report(expected_labels, predicted_labels, LABELS).render())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the sentiment API against a labeled CSV.")
    parser.add_argument("--csv", default="data/sample_reviews.csv", help="Path to labeled CSV file.")
    parser.add_argument("--url", default="http://localhost:8000/sentiment", help="Sentiment endpoint URL.")
    parser.add_argument(
        "--batch", action="store_true", help="Send the whole CSV to /sentiment/batch in one call instead of row by row."
    )
    args = parser.parse_args()

    if args.batch:
        evaluate_batch(args.csv, args.url)
    else:
        evaluate(args.csv, args.url)
