"""Unit tests for memory system."""

import pytest
from unittest.mock import AsyncMock, patch

from src.memory.manager import MemoryManager
from src.memory.short_term import ShortTermMemory


class TestShortTermMemory:
    """Tests for short-term memory."""

    @pytest.fixture
    def memory(self):
        return ShortTermMemory(ttl_seconds=3600)

    def test_conversation_key(self, memory):
        """Test conversation key generation."""
        key = memory._conversation_key("conv-123")
        assert key == "conv:conv-123"

    def test_context_key(self, memory):
        """Test context key generation."""
        key = memory._context_key("conv-123")
        assert key == "ctx:conv-123"

    def test_task_key(self, memory):
        """Test task key generation."""
        key = memory._task_key("conv-123")
        assert key == "task:conv-123"

    @pytest.mark.asyncio
    async def test_store_message(self, memory, mock_redis):
        """Test storing a message."""
        with patch("src.memory.short_term.redis_client", mock_redis):
            await memory.store_message(
                conversation_id="conv-123",
                role="user",
                content="Hello",
            )

            mock_redis.client.rpush.assert_called_once()
            mock_redis.client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_messages(self, memory, mock_redis):
        """Test getting messages."""
        import json

        mock_redis.client.lrange = AsyncMock(
            return_value=[
                json.dumps({"role": "user", "content": "Hello", "metadata": {}}),
                json.dumps({"role": "assistant", "content": "Hi!", "metadata": {}}),
            ]
        )

        with patch("src.memory.short_term.redis_client", mock_redis):
            messages = await memory.get_messages("conv-123")

            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_set_context(self, memory, mock_redis):
        """Test setting context."""
        with patch("src.memory.short_term.redis_client", mock_redis):
            await memory.set_context(
                conversation_id="conv-123",
                context={"topic": "deployment"},
            )

            mock_redis.client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_context(self, memory, mock_redis):
        """Test getting context."""
        import json

        mock_redis.client.get = AsyncMock(
            return_value=json.dumps({"topic": "deployment"})
        )

        with patch("src.memory.short_term.redis_client", mock_redis):
            context = await memory.get_context("conv-123")

            assert context["topic"] == "deployment"

    @pytest.mark.asyncio
    async def test_get_context_none(self, memory, mock_redis):
        """Test getting non-existent context."""
        mock_redis.client.get = AsyncMock(return_value=None)

        with patch("src.memory.short_term.redis_client", mock_redis):
            context = await memory.get_context("conv-123")

            assert context is None


class TestMemoryManager:
    """Tests for memory manager."""

    @pytest.fixture
    def manager(self):
        return MemoryManager()

    @pytest.mark.asyncio
    async def test_get_context_for_query(self, manager, mock_redis, mock_qdrant):
        """Test getting context for a query."""
        with patch.object(manager.short_term, "get_messages", AsyncMock(return_value=[])):
            with patch.object(manager.short_term, "get_context", AsyncMock(return_value={})):
                with patch.object(manager.user, "get_user_context", AsyncMock(return_value=[])):
                    with patch.object(manager.team, "get_team_context", AsyncMock(return_value=[])):
                        with patch.object(manager.org, "search", AsyncMock(return_value=[])):
                            context = await manager.get_context_for_query(
                                query="How do I deploy?",
                                user_id="user-123",
                                team_id="team-456",
                                conversation_id="conv-789",
                            )

                            assert "short_term" in context
                            assert "user" in context
                            assert "team" in context
                            assert "org" in context

    def test_format_context_for_prompt_empty(self, manager):
        """Test formatting empty context."""
        result = manager.format_context_for_prompt({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_format_context_for_prompt(self, manager):
        """Test formatting context for prompt."""
        context = {
            "short_term": {"context": {"topic": "deployment"}},
            "user": [{"text": "User prefers CLI tools"}],
            "team": [{"text": "Team uses GitHub Actions"}],
            "org": [{"text": "Company policy on deployments"}],
        }

        result = await manager.format_context_for_prompt(context)

        assert "deployment" in result
        assert "User" in result
        assert "Team" in result
        assert "Organization" in result

    def test_format_dict(self, manager):
        """Test dictionary formatting."""
        d = {"key1": "value1", "key2": "value2"}
        result = manager._format_dict(d)

        assert "key1: value1" in result
        assert "key2: value2" in result

    @pytest.mark.asyncio
    async def test_store_conversation_memory(self, manager, mock_redis, mock_qdrant):
        """Test storing conversation memory."""
        with patch.object(manager.short_term, "store_message", AsyncMock()):
            with patch.object(manager.user, "store_interaction", AsyncMock()):
                await manager.store_conversation_memory(
                    conversation_id="conv-123",
                    user_id="user-456",
                    query="How do I deploy?",
                    response="You can deploy using...",
                    topics=["deployment"],
                )

                # Should store in short-term (2 calls for query and response)
                assert manager.short_term.store_message.call_count == 2
