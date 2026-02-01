"""Unit tests for agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.orchestrator.intents import Intent, IntentClassifier
from src.agents.knowledge.agent import KnowledgeAgent
from src.agents.onboarding.flows import (
    OnboardingPhase,
    get_flow_for_user,
    get_next_task,
    calculate_progress,
    ENGINEERING_FLOW,
)


class TestIntentClassifier:
    """Tests for intent classification."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.asyncio
    async def test_classify_knowledge_intent(self, classifier, mock_llm):
        """Test classification of knowledge queries."""
        with patch.object(classifier, "client", mock_llm):
            mock_llm.messages.create = AsyncMock(
                return_value=MagicMock(
                    content=[MagicMock(text="knowledge|0.95")]
                )
            )

            intent, confidence = await classifier.classify(
                "How do we deploy to production?"
            )

            assert intent == Intent.KNOWLEDGE
            assert confidence == 0.95

    @pytest.mark.asyncio
    async def test_classify_onboarding_intent(self, classifier, mock_llm):
        """Test classification of onboarding queries."""
        with patch.object(classifier, "client", mock_llm):
            mock_llm.messages.create = AsyncMock(
                return_value=MagicMock(
                    content=[MagicMock(text="onboarding|0.9")]
                )
            )

            intent, confidence = await classifier.classify(
                "I just joined, where do I start?"
            )

            assert intent == Intent.ONBOARDING
            assert confidence == 0.9

    @pytest.mark.asyncio
    async def test_classify_team_analysis_intent(self, classifier, mock_llm):
        """Test classification of team analysis queries."""
        with patch.object(classifier, "client", mock_llm):
            mock_llm.messages.create = AsyncMock(
                return_value=MagicMock(
                    content=[MagicMock(text="team_analysis|0.95")]
                )
            )

            intent, confidence = await classifier.classify(
                "What's our team velocity this sprint?"
            )

            assert intent == Intent.TEAM_ANALYSIS
            assert confidence == 0.95

    @pytest.mark.asyncio
    async def test_classify_direct_response(self, classifier, mock_llm):
        """Test classification of simple queries."""
        with patch.object(classifier, "client", mock_llm):
            mock_llm.messages.create = AsyncMock(
                return_value=MagicMock(
                    content=[MagicMock(text="direct_response|1.0")]
                )
            )

            intent, confidence = await classifier.classify("Hi!")

            assert intent == Intent.DIRECT_RESPONSE
            assert confidence == 1.0


class TestOnboardingFlows:
    """Tests for onboarding flows."""

    def test_get_flow_for_engineer(self):
        """Test getting flow for software engineer."""
        flow = get_flow_for_user(
            role="Software Engineer",
            department="Engineering",
        )

        assert flow.id == "engineering"
        assert len(flow.tasks) > 0

    def test_get_flow_for_product_manager(self):
        """Test getting flow for product manager."""
        flow = get_flow_for_user(
            role="Product Manager",
            department="Product",
        )

        assert flow.id == "product"

    def test_get_general_flow_fallback(self):
        """Test fallback to general flow."""
        flow = get_flow_for_user(
            role="Unknown Role",
            department="Unknown Department",
        )

        assert flow.id == "general"

    def test_get_next_task(self):
        """Test getting next task in flow."""
        completed = []
        next_task = get_next_task(ENGINEERING_FLOW, completed)

        assert next_task is not None
        assert next_task.id == ENGINEERING_FLOW.tasks[0].id

    def test_get_next_task_with_completed(self):
        """Test getting next task with some completed."""
        completed = [ENGINEERING_FLOW.tasks[0].id]
        next_task = get_next_task(ENGINEERING_FLOW, completed)

        assert next_task is not None
        assert next_task.id == ENGINEERING_FLOW.tasks[1].id

    def test_get_next_task_all_completed(self):
        """Test getting next task when all completed."""
        completed = [t.id for t in ENGINEERING_FLOW.tasks]
        next_task = get_next_task(ENGINEERING_FLOW, completed)

        assert next_task is None

    def test_calculate_progress_empty(self):
        """Test progress calculation with no completed tasks."""
        progress, phase = calculate_progress(ENGINEERING_FLOW, [])

        assert progress == 0
        assert phase == ENGINEERING_FLOW.tasks[0].phase

    def test_calculate_progress_partial(self):
        """Test progress calculation with partial completion."""
        completed = [ENGINEERING_FLOW.tasks[0].id, ENGINEERING_FLOW.tasks[1].id]
        progress, phase = calculate_progress(ENGINEERING_FLOW, completed)

        expected_progress = int((2 / len(ENGINEERING_FLOW.tasks)) * 100)
        assert progress == expected_progress
        assert phase is not None

    def test_calculate_progress_complete(self):
        """Test progress calculation with all tasks complete."""
        completed = [t.id for t in ENGINEERING_FLOW.tasks]
        progress, phase = calculate_progress(ENGINEERING_FLOW, completed)

        assert progress == 100
        assert phase == OnboardingPhase.COMPLETE


class TestKnowledgeAgent:
    """Tests for knowledge agent."""

    @pytest.fixture
    def agent(self):
        return KnowledgeAgent()

    def test_format_retrieved_docs_empty(self, agent):
        """Test formatting with no documents."""
        result = agent._format_retrieved_docs([])
        assert "No relevant documents" in result

    def test_format_retrieved_docs(self, agent):
        """Test formatting with documents."""
        docs = [
            {
                "title": "Test Doc",
                "text": "Test content",
                "source": "jira",
                "node_type": "Context",
            }
        ]
        result = agent._format_retrieved_docs(docs)

        assert "Test Doc" in result
        assert "Test content" in result

    def test_format_memory_context_empty(self, agent):
        """Test formatting with empty memory."""
        result = agent._format_memory_context({})
        assert "No additional context" in result

    def test_format_memory_context(self, agent):
        """Test formatting with memory context."""
        memory = {
            "user": [{"text": "User preference"}],
            "team": [{"text": "Team norm"}],
        }
        result = agent._format_memory_context(memory)

        assert "User preference" in result
        assert "Team norm" in result
