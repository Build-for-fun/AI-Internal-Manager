"""Orchestrator agent that routes queries to specialized agents."""

from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.agents.orchestrator.graph import ConversationState, orchestrator_graph
from src.memory.manager import memory_manager

logger = structlog.get_logger()


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that manages conversation flow.

    This agent:
    1. Classifies user intent
    2. Routes to the appropriate specialized agent
    3. Manages conversation state
    4. Handles memory retrieval and storage
    """

    def __init__(self):
        super().__init__(
            name="orchestrator",
            description="Routes queries to appropriate specialized agents",
        )

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a query by routing to the appropriate agent.

        Args:
            query: The user's query
            context: Context including user info, conversation ID, etc.

        Returns:
            Response from the appropriate agent
        """
        # Get conversation ID
        conversation_id = context.get("conversation_id", "")
        user_id = context.get("user_id", "")

        # Retrieve relevant memory
        memory_context = await memory_manager.get_context_for_query(
            query=query,
            user_id=user_id,
            team_id=context.get("team_id"),
            conversation_id=conversation_id,
        )

        # Build initial state
        state: ConversationState = {
            "messages": context.get("messages", []),
            "current_query": query,
            "intent": None,
            "intent_confidence": 0.0,
            "active_agent": None,
            "user_id": user_id,
            "user_name": context.get("user_name"),
            "user_role": context.get("user_role"),
            "user_department": context.get("user_department"),
            "user_team": context.get("user_team"),
            "conversation_id": conversation_id,
            "conversation_type": context.get("conversation_type", "chat"),
            "memory_context": memory_context,
            "response": None,
            "sources": None,
            "error": None,
        }

        try:
            # Run the orchestrator graph
            result = await orchestrator_graph.ainvoke(state)

            response = result.get("response", "I'm sorry, I couldn't process your request.")
            sources = result.get("sources", [])
            active_agent = result.get("active_agent", "unknown")

            # Store in memory
            await memory_manager.store_conversation_memory(
                conversation_id=conversation_id,
                user_id=user_id,
                query=query,
                response=response,
                topics=self._extract_topics(query, response),
            )

            logger.info(
                "Query processed",
                agent=active_agent,
                intent=result.get("intent"),
                confidence=result.get("intent_confidence"),
            )

            return {
                "response": response,
                "sources": sources,
                "agent": active_agent,
                "intent": result.get("intent"),
                "metadata": {
                    "intent_confidence": result.get("intent_confidence"),
                },
            }

        except Exception as e:
            logger.error("Orchestrator failed", error=str(e))
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "sources": [],
                "agent": "orchestrator",
                "error": str(e),
            }

    def _extract_topics(self, query: str, response: str) -> list[str]:
        """Extract topics from query and response for memory storage.

        Simple keyword extraction. In production, use NLP or LLM.
        """
        # Combine and extract potential topics
        text = f"{query} {response}".lower()

        # Simple topic keywords
        topic_indicators = {
            "deployment": ["deploy", "release", "production", "staging"],
            "authentication": ["auth", "login", "sso", "oauth"],
            "database": ["database", "db", "sql", "migration"],
            "api": ["api", "endpoint", "rest", "graphql"],
            "testing": ["test", "testing", "qa", "quality"],
            "ci_cd": ["ci", "cd", "pipeline", "build"],
            "monitoring": ["monitor", "alert", "metric", "log"],
            "security": ["security", "permission", "access", "role"],
        }

        topics = []
        for topic, keywords in topic_indicators.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)

        return topics[:3]  # Return top 3 topics

    async def stream_process(
        self,
        query: str,
        context: dict[str, Any],
    ):
        """Stream a response (for future streaming support).

        Yields response chunks as they're generated.
        """
        # For now, just yield the full response
        result = await self.process(query, context)
        yield result


# Singleton instance
orchestrator_agent = OrchestratorAgent()
