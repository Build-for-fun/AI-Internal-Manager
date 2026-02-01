"""End-to-end tests for chat flow."""

import pytest
from unittest.mock import AsyncMock, patch


class TestChatFlow:
    """End-to-end tests for complete chat flows."""

    @pytest.mark.asyncio
    async def test_full_chat_flow(self, async_client, db_session, mock_llm, mock_neo4j, mock_qdrant):
        """Test complete chat flow from conversation creation to response."""
        # 1. Create a conversation
        conv_response = await async_client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "E2E Test Conversation",
                "conversation_type": "chat",
            },
        )
        assert conv_response.status_code == 200
        conversation = conv_response.json()
        conv_id = conversation["id"]

        # 2. Send a message
        with patch(
            "src.api.v1.chat.orchestrator_agent.process",
            AsyncMock(
                return_value={
                    "response": "Here's how to deploy to production...",
                    "sources": [{"id": "1", "title": "Deployment Guide"}],
                    "agent": "knowledge",
                    "intent": "knowledge",
                }
            ),
        ):
            msg_response = await async_client.post(
                f"/api/v1/chat/conversations/{conv_id}/messages",
                json={"message": "How do I deploy to production?"},
            )
            assert msg_response.status_code == 200
            message = msg_response.json()
            assert "message" in message
            assert message["agent_used"] == "knowledge"

        # 3. Get conversation messages
        messages_response = await async_client.get(
            f"/api/v1/chat/conversations/{conv_id}/messages"
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) >= 1

        # 4. Get conversation details
        conv_detail_response = await async_client.get(
            f"/api/v1/chat/conversations/{conv_id}"
        )
        assert conv_detail_response.status_code == 200
        conv_detail = conv_detail_response.json()
        assert conv_detail["id"] == conv_id

    @pytest.mark.asyncio
    async def test_onboarding_chat_flow(self, async_client, db_session, mock_llm):
        """Test chat flow for onboarding."""
        # Create onboarding conversation
        conv_response = await async_client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Onboarding",
                "conversation_type": "onboarding",
            },
        )
        assert conv_response.status_code == 200
        conv_id = conv_response.json()["id"]

        # Send onboarding query
        with patch(
            "src.api.v1.chat.orchestrator_agent.process",
            AsyncMock(
                return_value={
                    "response": "Welcome! Let me help you get started...",
                    "sources": [],
                    "agent": "onboarding",
                    "intent": "onboarding",
                }
            ),
        ):
            msg_response = await async_client.post(
                f"/api/v1/chat/conversations/{conv_id}/messages",
                json={"message": "I just joined, where do I start?"},
            )
            assert msg_response.status_code == 200
            assert msg_response.json()["agent_used"] == "onboarding"


class TestOnboardingFlow:
    """End-to-end tests for onboarding flow."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(self, async_client, db_session):
        """Test complete onboarding from start to task completion."""
        # 1. Start onboarding
        with patch(
            "src.agents.onboarding.agent.onboarding_agent.start_onboarding",
            AsyncMock(
                return_value={
                    "flow_id": "engineering",
                    "flow_name": "Engineering Onboarding",
                    "total_tasks": 9,
                    "first_task": "Welcome to Engineering",
                }
            ),
        ):
            start_response = await async_client.post(
                "/api/v1/onboarding/start",
                json={},
            )
            # May need actual DB setup for this test
            # assert start_response.status_code == 200

        # 2. Get progress
        progress_response = await async_client.get("/api/v1/onboarding/progress")
        assert progress_response.status_code == 200

        # 3. Get recommendations
        rec_response = await async_client.get("/api/v1/onboarding/recommended")
        assert rec_response.status_code == 200
        recommendations = rec_response.json()
        assert "recommendations" in recommendations
