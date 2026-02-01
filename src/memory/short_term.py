"""Short-term memory using Redis for conversation context."""

import json
from datetime import timedelta
from typing import Any

import redis.asyncio as redis
import structlog

from src.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Async Redis client for short-term memory."""

    def __init__(self):
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self.ping()
        logger.info("Redis connected")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")

    @property
    def client(self) -> redis.Redis | None:
        """Get the Redis client."""
        return self._client

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        if not self._client:
            return False
        return await self.client.ping()


# Singleton instance
redis_client = RedisClient()


class ShortTermMemory:
    """Short-term memory manager for conversation context.

    Stores:
    - Recent conversation history
    - Active task state
    - Temporary context
    """

    def __init__(self, ttl_seconds: int | None = None):
        self.ttl = ttl_seconds or settings.redis_conversation_ttl

    def _conversation_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation."""
        return f"conv:{conversation_id}"

    def _context_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation context."""
        return f"ctx:{conversation_id}"

    def _task_key(self, conversation_id: str) -> str:
        """Get Redis key for active task."""
        return f"task:{conversation_id}"

    async def store_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a message in conversation history."""
        if not redis_client.client:
            return

        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }

        key = self._conversation_key(conversation_id)
        try:
            await redis_client.client.rpush(key, json.dumps(message))
            await redis_client.client.expire(key, self.ttl)
        except Exception as e:
            logger.warning("Redis store failed", error=str(e))

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent messages."""
        if not redis_client.client:
            return []

        key = self._conversation_key(conversation_id)
        try:
            raw_messages = await redis_client.client.lrange(key, -limit, -1)
            return [json.loads(msg) for msg in raw_messages]
        except Exception as e:
            logger.warning("Redis fetch failed", error=str(e))
            return []

    async def clear_messages(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if not redis_client.client:
            return
            
        key = self._conversation_key(conversation_id)
        try:
            await redis_client.client.delete(key)
        except Exception as e:
            logger.warning("Redis delete failed", error=str(e))

    async def set_context(
        self,
        conversation_id: str,
        context: dict[str, Any],
    ) -> None:
        """Set conversation context."""
        if not redis_client.client:
            return
            
        key = self._context_key(conversation_id)
        try:
            await redis_client.client.set(
                key,
                json.dumps(context),
                ex=self.ttl,
            )
        except Exception as e:
            logger.warning("Redis set context failed", error=str(e))

    async def get_context(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        """Get conversation context."""
        if not redis_client.client:
            return None
            
        key = self._context_key(conversation_id)
        try:
            data = await redis_client.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Redis get context failed", error=str(e))
            return None

    async def update_context(
        self,
        conversation_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update conversation context (merge with existing)."""
        current = await self.get_context(conversation_id) or {}
        current.update(updates)
        await self.set_context(conversation_id, current)
        return current

    async def set_active_task(
        self,
        conversation_id: str,
        task: dict[str, Any],
    ) -> None:
        """Set active task for conversation."""
        if not redis_client.client:
            return
            
        key = self._task_key(conversation_id)
        try:
            await redis_client.client.set(
                key,
                json.dumps(task),
                ex=self.ttl,
            )
        except Exception as e:
            logger.warning("Redis set task failed", error=str(e))

    async def get_active_task(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        """Get active task for conversation."""
        if not redis_client.client:
            return None
            
        key = self._task_key(conversation_id)
        try:
            data = await redis_client.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Redis get task failed", error=str(e))
            return None

    async def clear_active_task(self, conversation_id: str) -> None:
        """Clear active task."""
        if not redis_client.client:
            return
            
        key = self._task_key(conversation_id)
        try:
            await redis_client.client.delete(key)
        except Exception as e:
            logger.warning("Redis clear task failed", error=str(e))

    async def cleanup_expired(self) -> int:
        """Cleanup is handled by Redis TTL, this is a no-op."""
        return 0


# Singleton instance
short_term_memory = ShortTermMemory()
