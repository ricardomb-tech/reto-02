import asyncio
from unittest.mock import patch

import pytest

from app.cache import _build_backend
from app.cache_backends import InMemoryCacheBackend, RedisCacheBackend


def test_in_memory_backend_roundtrip():
    backend = InMemoryCacheBackend(maxsize=10, ttl=60)

    async def scenario():
        assert await backend.get("key") is None
        await backend.set("key", {"label": "POSITIVE", "score": 0.9})
        assert await backend.get("key") == {"label": "POSITIVE", "score": 0.9}

    asyncio.run(scenario())


def test_build_backend_defaults_to_in_memory():
    with patch("app.cache.settings.cache_backend", "memory"):
        assert isinstance(_build_backend(), InMemoryCacheBackend)


def test_build_backend_selects_redis_when_configured():
    with patch("app.cache.settings.cache_backend", "redis"), patch("app.cache.settings.redis_url", "redis://localhost:6379/0"):
        assert isinstance(_build_backend(), RedisCacheBackend)


def _redis_available(url: str) -> bool:
    import redis

    try:
        redis.Redis.from_url(url, socket_connect_timeout=0.2).ping()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _redis_available("redis://localhost:6379/0"), reason="no local Redis available")
def test_redis_backend_roundtrip():
    backend = RedisCacheBackend(url="redis://localhost:6379/0", ttl=60)

    async def scenario():
        await backend.set("test:cache_backend:key", {"label": "NEGATIVE", "score": 0.8})
        assert await backend.get("test:cache_backend:key") == {"label": "NEGATIVE", "score": 0.8}

    asyncio.run(scenario())
