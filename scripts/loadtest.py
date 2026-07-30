"""Small load test for the sentiment API: fires concurrent requests and reports latency.

Usage:
    python scripts/loadtest.py --url http://localhost:8000/sentiment --requests 100 --concurrency 10

Uses httpx + asyncio (both already project dependencies) instead of a separate tool
like k6 or locust, so there's nothing extra to install to reproduce the numbers.
"""
import argparse
import asyncio
import time

import httpx


async def _one_request(client: httpx.AsyncClient, url: str, text: str, semaphore: asyncio.Semaphore) -> float:
    async with semaphore:
        started = time.monotonic()
        try:
            response = await client.post(url, json={"text": text}, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError:
            return -1.0
        return (time.monotonic() - started) * 1000


def _percentile(sorted_values: list, pct: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return sorted_values[index]


async def run(url: str, total_requests: int, concurrency: int, text: str) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    started_at = time.monotonic()

    async with httpx.AsyncClient() as client:
        tasks = [_one_request(client, url, text, semaphore) for _ in range(total_requests)]
        latencies_ms = await asyncio.gather(*tasks)

    elapsed = time.monotonic() - started_at
    ok_latencies = sorted(latency for latency in latencies_ms if latency >= 0)
    errors = len(latencies_ms) - len(ok_latencies)
    throughput = len(ok_latencies) / elapsed if elapsed > 0 else 0.0

    print(f"Requests: {total_requests} (concurrency={concurrency}), {errors} errors, {elapsed:.2f}s total")
    print(f"Throughput: {throughput:.1f} req/s")
    if ok_latencies:
        print(f"Latency p50: {_percentile(ok_latencies, 0.50):.1f} ms")
        print(f"Latency p95: {_percentile(ok_latencies, 0.95):.1f} ms")
        print(f"Latency p99: {_percentile(ok_latencies, 0.99):.1f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test the /sentiment endpoint.")
    parser.add_argument("--url", default="http://localhost:8000/sentiment", help="Sentiment endpoint URL.")
    parser.add_argument("--requests", type=int, default=100, help="Total number of requests to send.")
    parser.add_argument("--concurrency", type=int, default=10, help="Max requests in flight at once.")
    parser.add_argument("--text", default="I absolutely loved this movie!", help="Text to send on every request.")
    args = parser.parse_args()

    asyncio.run(run(args.url, args.requests, args.concurrency, args.text))
