"""Cache backend implementations behind a common async interface. See ADR-0012."""
import json
from typing import Protocol

from cachetools import TTLCache


class CacheBackend(Protocol):
    async def get(self, key: str) -> dict | None: ...

    async def set(self, key: str, value: dict) -> None: ...


class InMemoryCacheBackend:
    """Default backend: process-local, bounded, TTL-based. No external service required."""

    def __init__(self, maxsize: int, ttl: int):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    async def get(self, key: str):
        return self._cache.get(key)

    async def set(self, key: str, value: dict) -> None:
        self._cache[key] = value


class RedisCacheBackend:
    """Optional backend for sharing the cache across multiple replicas. Opt-in via CACHE_BACKEND=redis."""

    def __init__(self, url: str, ttl: int):
        import redis.asyncio as redis  # imported lazily: only required when this backend is selected

        self._client = redis.from_url(url)
        self._ttl = ttl

    async def get(self, key: str):
        raw = await self._client.get(key)
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: dict) -> None:
        await self._client.setex(key, self._ttl, json.dumps(value))
