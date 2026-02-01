"""Intent classification for routing queries to appropriate agents."""

from enum import Enum
from typing import Any

from anthropic import AsyncAnthropic

from src.config import settings


class Intent(str, Enum):
    """Possible intents for user queries."""

    KNOWLEDGE = "knowledge"  # Questions about company knowledge, processes, docs
    ONBOARDING = "onboarding"  # Onboarding-related queries
    TEAM_ANALYSIS = "team_analysis"  # Team health, metrics, analytics
    DIRECT_RESPONSE = "direct_response"  # Simple queries that don't need agents
    CLARIFICATION = "clarification"  # Need more information from user


class IntentClassifier:
    """Classifies user intents to route to appropriate agents.

    Uses Claude for classification with few-shot examples.
    """

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

    async def classify(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[Intent, float]:
        """Classify the intent of a user query.

        Returns:
            A tuple of (intent, confidence)
        """
        system_prompt = """You are an intent classifier for an internal company AI assistant.
Your job is to determine which specialized agent should handle a user's query.

Available intents:
- knowledge: Questions about company documentation, processes, projects, tools, or past decisions
- onboarding: Questions from new employees, requests for onboarding help, introductions to the company
- team_analysis: Questions about team performance, metrics, workload, velocity, bottlenecks
- direct_response: Simple greetings, thanks, or questions that don't require specialized knowledge
- clarification: When the query is too vague or ambiguous to classify

Respond with ONLY the intent name, followed by a confidence score from 0-1.
Format: intent_name|confidence

Examples:
User: "How do we deploy to production?"
Response: knowledge|0.95

User: "I just joined the team, where do I start?"
Response: onboarding|0.9

User: "What's our team's velocity this sprint?"
Response: team_analysis|0.95

User: "Hi!"
Response: direct_response|1.0

User: "help"
Response: clarification|0.7
"""

        user_message = f"User query: {query}"
        if context:
            if context.get("is_new_employee"):
                user_message += "\n[Context: User is a new employee in onboarding]"
            if context.get("current_flow") == "onboarding":
                user_message += "\n[Context: User is currently in an onboarding flow]"

        response = await self.client.messages.create(
            model="claude-3-5-haiku-20241022",  # Use fast model for classification
            max_tokens=50,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        result = response.content[0].text.strip()

        try:
            intent_str, confidence_str = result.split("|")
            intent = Intent(intent_str.strip())
            confidence = float(confidence_str.strip())
            return intent, confidence
        except (ValueError, KeyError):
            # Default to knowledge if parsing fails
            return Intent.KNOWLEDGE, 0.5


# Singleton instance
intent_classifier = IntentClassifier()
