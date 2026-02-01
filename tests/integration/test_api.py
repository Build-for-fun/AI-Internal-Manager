"""Integration tests for API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestChatAPI:
    """Tests for chat API endpoints."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, async_client, db_session):
        """Test creating a conversation."""
        response = await async_client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Test Conversation",
                "conversation_type": "chat",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_conversations(self, async_client, db_session):
        """Test listing conversations."""
        # Create a conversation first
        await async_client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test"},
        )

        response = await async_client.get("/api/v1/chat/conversations")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_send_message(self, async_client, db_session, mock_llm):
        """Test sending a message."""
        # Create conversation
        conv_response = await async_client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test"},
        )
        conv_id = conv_response.json()["id"]

        # Mock the orchestrator
        with patch(
            "src.api.v1.chat.orchestrator_agent.process",
            AsyncMock(
                return_value={
                    "response": "Test response",
                    "sources": [],
                    "agent": "knowledge",
                }
            ),
        ):
            response = await async_client.post(
                f"/api/v1/chat/conversations/{conv_id}/messages",
                json={"message": "Hello"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"]["content"] == "Test response"


class TestKnowledgeAPI:
    """Tests for knowledge API endpoints."""

    @pytest.mark.asyncio
    async def test_search_knowledge(self, async_client, mock_neo4j, mock_qdrant):
        """Test knowledge search."""
        with patch(
            "src.agents.knowledge.retrieval.hybrid_retriever.retrieve",
            AsyncMock(
                return_value=[
                    {
                        "id": "1",
                        "title": "Test",
                        "text": "Test content",
                        "node_type": "Context",
                        "score": 0.9,
                    }
                ]
            ),
        ):
            response = await async_client.post(
                "/api/v1/knowledge/search",
                json={"query": "deployment process"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert data["query"] == "deployment process"

    @pytest.mark.asyncio
    async def test_get_hierarchy(self, async_client, mock_neo4j):
        """Test getting knowledge hierarchy."""
        with patch(
            "src.knowledge.textbook.hierarchy.hierarchy_manager.get_hierarchy",
            AsyncMock(
                return_value={
                    "departments": [],
                    "total_nodes": 0,
                }
            ),
        ):
            response = await async_client.get("/api/v1/knowledge/graph/hierarchy")

            assert response.status_code == 200
            data = response.json()
            assert "departments" in data


class TestOnboardingAPI:
    """Tests for onboarding API endpoints."""

    @pytest.mark.asyncio
    async def test_list_flows(self, async_client):
        """Test listing onboarding flows."""
        response = await async_client.get("/api/v1/onboarding/flows")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_flow(self, async_client):
        """Test getting specific flow."""
        response = await async_client.get("/api/v1/onboarding/flows/engineering")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "engineering"
        assert "tasks" in data

    @pytest.mark.asyncio
    async def test_get_flow_not_found(self, async_client):
        """Test getting non-existent flow."""
        response = await async_client.get("/api/v1/onboarding/flows/nonexistent")

        assert response.status_code == 404


class TestAnalyticsAPI:
    """Tests for analytics API endpoints."""

    @pytest.mark.asyncio
    async def test_get_team_health(self, async_client):
        """Test getting team health."""
        with patch(
            "src.agents.team_analysis.agent.team_analysis_agent.get_team_health",
            AsyncMock(
                return_value=type(
                    "Report",
                    (),
                    {
                        "team_id": "team-1",
                        "team_name": "Platform",
                        "generated_at": "2024-01-01T00:00:00",
                        "overall_health": type("H", (), {"value": "healthy"})(),
                        "overall_score": 85,
                        "metrics": [],
                        "insights": [],
                        "recommendations": [],
                    },
                )()
            ),
        ):
            response = await async_client.get("/api/v1/analytics/team/team-1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["team_id"] == "team-1"
            assert "overall_score" in data
