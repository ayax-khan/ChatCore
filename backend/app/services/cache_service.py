import json
import hashlib
import logging
from typing import Optional, Any
from datetime import timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self.client = None
        self._connected = False

    async def init(self):
        try:
            import redis.asyncio as redis
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.client.ping()
            self._connected = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}. Running without cache.")
            self._connected = False

    async def close(self):
        if self.client and self._connected:
            await self.client.close()
            self._connected = False

    def _make_key(self, prefix: str, *parts: str) -> str:
        raw = ":".join(str(p) for p in parts)
        return f"chatcore:{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"

    async def get(self, key: str) -> Optional[str]:
        if not self._connected or not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        if not self._connected or not self.client:
            return
        try:
            await self.client.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    async def delete(self, key: str):
        if not self._connected or not self.client:
            return
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}")

    async def cache_answer(self, site_id: int, question: str, answer: str, ttl: int = 86400):
        key = self._make_key("answer", str(site_id), question.lower().strip())
        await self.set(key, answer, ttl)

    async def get_cached_answer(self, site_id: int, question: str) -> Optional[str]:
        key = self._make_key("answer", str(site_id), question.lower().strip())
        return await self.get(key)

    async def cache_embedding(self, text: str, embedding: list[float], ttl: int = 86400 * 7):
        key = self._make_key("embedding", text)
        await self.set(key, json.dumps(embedding), ttl)

    async def get_cached_embedding(self, text: str) -> Optional[list[float]]:
        key = self._make_key("embedding", text)
        cached = await self.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def increment_rate_limit(self, key: str, limit: int = 60, window: int = 60) -> tuple[bool, int]:
        if not self._connected or not self.client:
            return True, 0
        try:
            current = await self.client.incr(key)
            if current == 1:
                await self.client.expire(key, window)
            return current <= limit, current
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True, 0

    async def get_usage_stats(self, business_id: int) -> dict:
        keys = {
            "total_queries": f"chatcore:usage:{business_id}:queries",
            "total_tokens": f"chatcore:usage:{business_id}:tokens",
            "total_cost": f"chatcore:usage:{business_id}:cost",
        }
        result = {}
        if self._connected and self.client:
            for name, key in keys.items():
                val = await self.client.get(key)
                result[name] = int(val) if val else 0
        else:
            result = {k: 0 for k in keys}
        return result

    async def increment_usage(self, business_id: int, tokens: int = 0, cost: float = 0.0):
        if not self._connected or not self.client:
            return
        try:
            pipe = self.client.pipeline()
            pipe.incr(f"chatcore:usage:{business_id}:queries", 1)
            pipe.incr(f"chatcore:usage:{business_id}:tokens", tokens)
            pipe.incrbyfloat(f"chatcore:usage:{business_id}:cost", cost)
            pipe.expire(f"chatcore:usage:{business_id}:queries", 86400 * 30)
            pipe.expire(f"chatcore:usage:{business_id}:tokens", 86400 * 30)
            pipe.expire(f"chatcore:usage:{business_id}:cost", 86400 * 30)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"Usage increment failed: {e}")
