"""Pytest fixtures and configuration."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.main import app
from src.models.base import Base
from src.models.database import get_db
from src.config import settings
from src.rbac.guards import rbac_guard
from src.rbac.models import AccessDecision, AccessLevel


# Test settings override
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        database_url="sqlite+aiosqlite:///./test.db",
        redis_url="redis://localhost:6379/15",
        neo4j_uri="bolt://localhost:7687",
        anthropic_api_key="test-api-key",
        debug=True,
    )


@pytest.fixture(autouse=True)
def force_anthropic_provider(monkeypatch):
    """Force anthropic provider for deterministic unit tests."""
    monkeypatch.setattr(settings, "llm_provider", "anthropic", raising=False)


@pytest.fixture(autouse=True)
def allow_all_rbac(monkeypatch):
    """Bypass RBAC checks in tests to focus on API behavior."""
    def _allow_access(*, context, resource, required_level=AccessLevel.READ, resource_attrs=None):
        return AccessDecision.allow(
            policy_id="test-allow",
            resource=resource,
            access_level=required_level,
        )

    monkeypatch.setattr(rbac_guard, "require_access", _allow_access)


# Event loop for async tests
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test database engine
@pytest.fixture(scope="session")
async def test_engine(test_settings):
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test.db",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# Test database session
@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# Override database dependency
@pytest.fixture
def override_get_db(db_session):
    """Override get_db dependency."""

    async def _override_get_db():
        yield db_session

    return _override_get_db


# Test client
@pytest.fixture
def client(override_get_db) -> Generator:
    """Create test client."""
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# Async test client
@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Mock LLM client
@pytest.fixture
def mock_llm():
    """Mock Anthropic client."""
    with patch("src.agents.base.AsyncAnthropic") as mock:
        mock_instance = MagicMock()
        mock_instance.messages.create = AsyncMock(
            return_value=MagicMock(
                content=[MagicMock(text="Test response", type="text")],
                stop_reason="end_turn",
                usage=MagicMock(input_tokens=100, output_tokens=50),
            )
        )
        mock.return_value = mock_instance
        yield mock_instance


# Mock Neo4j client
@pytest.fixture
def mock_neo4j():
    """Mock Neo4j client."""
    with patch("src.knowledge.graph.client.neo4j_client") as mock:
        mock.connect = AsyncMock()
        mock.close = AsyncMock()
        mock.verify_connectivity = AsyncMock(return_value=True)
        mock.create_node = AsyncMock(return_value={"id": "test-id", "title": "Test"})
        mock.get_node = AsyncMock(return_value={"id": "test-id", "title": "Test"})
        mock.fulltext_search = AsyncMock(return_value=[])
        yield mock


# Mock Redis client
@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("src.memory.short_term.redis_client") as mock:
        mock.connect = AsyncMock()
        mock.close = AsyncMock()
        mock.ping = AsyncMock(return_value=True)
        mock.client.get = AsyncMock(return_value=None)
        mock.client.set = AsyncMock()
        mock.client.rpush = AsyncMock()
        mock.client.lrange = AsyncMock(return_value=[])
        yield mock


# Mock Qdrant client
@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    with patch("src.knowledge.indexing.embedder.embedder") as mock:
        mock.init_collections = AsyncMock()
        mock.generate_embedding = AsyncMock(return_value=[0.1] * 1024)
        mock.store_embedding = AsyncMock(return_value="test-point-id")
        mock.search = AsyncMock(return_value=[])
        yield mock


# Sample user fixture
@pytest.fixture
def sample_user():
    """Create sample user data."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "Software Engineer",
        "department": "Engineering",
        "team": "Platform",
    }


# Sample conversation fixture
@pytest.fixture
def sample_conversation(sample_user):
    """Create sample conversation data."""
    return {
        "id": "test-conversation-id",
        "user_id": sample_user["id"],
        "title": "Test Conversation",
        "conversation_type": "chat",
        "metadata": {},
    }
