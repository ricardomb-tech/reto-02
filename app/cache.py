"""Cache facade for sentiment results, keyed by normalized text.

Delegates to whichever backend CACHE_BACKEND selects (see app/cache_backends.py
and ADR-0012); callers here never need to know which one is in use.
"""
import hashlib

from prometheus_client import Counter

from app.cache_backends import InMemoryCacheBackend, RedisCacheBackend
from app.config import settings

CACHE_HITS = Counter("sentiment_cache_hits_total", "Sentiment lookups served from cache.")
CACHE_MISSES = Counter("sentiment_cache_misses_total", "Sentiment lookups that were not in cache.")


def _build_backend():
    if settings.cache_backend == "redis":
        return RedisCacheBackend(url=settings.redis_url, ttl=settings.cache_ttl_seconds)
    return InMemoryCacheBackend(maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds)


_backend = _build_backend()


def _key_for(text: str) -> str:
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def get_cached(text: str):
    result = await _backend.get(_key_for(text))
    if result is not None:
        CACHE_HITS.inc()
    else:
        CACHE_MISSES.inc()
    return result


async def set_cached(text: str, value: dict) -> None:
    await _backend.set(_key_for(text), value)
