"""In-memory TTL cache for sentiment results, keyed by normalized text."""
import hashlib

from cachetools import TTLCache

from app.config import settings

_cache: TTLCache = TTLCache(maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds)


def _key_for(text: str) -> str:
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached(text: str):
    return _cache.get(_key_for(text))


def set_cached(text: str, value: dict) -> None:
    _cache[_key_for(text)] = value
