"""Intent classification for routing queries to appropriate agents."""

from enum import Enum
from typing import Any

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.config import settings


class Intent(str, Enum):
    """Possible intents for user queries."""

    KNOWLEDGE = "knowledge"  # Questions about company knowledge, processes, docs
    ONBOARDING = "onboarding"  # Onboarding-related queries
    TEAM_ANALYSIS = "team_analysis"  # Team health, metrics, analytics
    DIRECT_RESPONSE = "direct_response"  # Simple queries, general knowledge, or greetings that don't need company data
    CLARIFICATION = "clarification"  # Need more information from user


class IntentClassifier:
    """Classifies user intents to route to appropriate agents.

    Uses Claude for classification with few-shot examples.
    """

    def __init__(self):
        self.provider = settings.llm_provider
        if self.provider == "keywords_ai":
            self.client = AsyncOpenAI(
                api_key=settings.keywords_ai_api_key.get_secret_value(),
                base_url=settings.keywords_ai_base_url,
            )
            self.model = settings.keywords_ai_default_model
        else:
            self.client = AsyncAnthropic(
                api_key=settings.anthropic_api_key.get_secret_value()
            )
            self.model = "claude-3-5-haiku-20241022"  # Use fast model for classification

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
- direct_response: Greetings, general knowledge questions, coding help, or queries not specific to company internal data
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

User: "What is a binary search tree?"
Response: direct_response|0.95

User: "Write a python script to parse JSON"
Response: direct_response|0.95

User: "help"
Response: clarification|0.7
"""

        user_message = f"User query: {query}"
        if context:
            if context.get("is_new_employee"):
                user_message += "\n[Context: User is a new employee in onboarding]"
            if context.get("current_flow") == "onboarding":
                user_message += "\n[Context: User is currently in an onboarding flow]"

        if self.provider == "keywords_ai":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=50,
            )
            result = response.choices[0].message.content.strip()
        else:
            response = await self.client.messages.create(
                model=self.model,
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
            # Default to direct_response if parsing fails or unclear
            return Intent.DIRECT_RESPONSE, 0.5


# Singleton instance
intent_classifier = IntentClassifier()
