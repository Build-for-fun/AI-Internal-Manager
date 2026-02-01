"""Intent classification for routing queries to appropriate agents."""

from enum import Enum
from typing import Any

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.config import settings

# Type alias for keyword arguments
KwargsDict = dict[str, Any]


class Intent(str, Enum):
    """Possible intents for user queries."""

    KNOWLEDGE = "knowledge"  # Questions about company knowledge, processes, docs
    ONBOARDING = "onboarding"  # Onboarding-related queries
    TEAM_ANALYSIS = "team_analysis"  # Team health, metrics, analytics
    EVALUATOR = "evaluator"  # LLM evaluation, quality assessment, model testing
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
            self.model = settings.anthropic_fast_model  # Use fast model for classification

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
- evaluator: Requests to evaluate LLM outputs, test model quality, run evaluations, or assess AI responses
- direct_response: Greetings, general knowledge questions, coding help, or queries not specific to company internal data
- clarification: When the query is too vague or ambiguous to classify AND there is no conversation history to provide context

IMPORTANT: When classifying follow-up questions, consider the conversation history.
- If the user asks "How do we secure it?" after asking about OAuth, classify as knowledge (about OAuth security)
- If the user says "Tell me more" after discussing deployment, classify as knowledge (about deployment)
- Follow-up questions that reference previous topics should inherit the intent of that topic

Respond with ONLY the intent name, followed by a confidence score from 0-1.
Format: intent_name|confidence

Examples:
User: "How do we deploy to production?"
Response: knowledge|0.95

User: "I just joined the team, where do I start?"
Response: onboarding|0.9

User: "What's our team's velocity this sprint?"
Response: team_analysis|0.95

User: "Evaluate the quality of this LLM response"
Response: evaluator|0.95

User: "Run evaluations on the chatbot output"
Response: evaluator|0.9

User: "Hi!"
Response: direct_response|1.0

User: "What is a binary search tree?"
Response: direct_response|0.95

User: "Write a python script to parse JSON"
Response: direct_response|0.95

User: "help" (with no prior conversation)
Response: clarification|0.7

User: "Tell me more about that" (after discussing OAuth)
Response: knowledge|0.9
"""

        user_message = f"User query: {query}"

        # Add conversation history context for follow-up understanding
        if context:
            messages = context.get("messages", [])
            if messages:
                # Include last 2-4 exchanges for context
                recent_messages = messages[-4:]
                history_text = "\n".join([
                    f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')[:200]}"
                    for m in recent_messages
                ])
                user_message = f"Conversation history:\n{history_text}\n\nNew user query: {query}"

            if context.get("is_new_employee"):
                user_message += "\n[Context: User is a new employee in onboarding]"
            if context.get("current_flow") == "onboarding":
                user_message += "\n[Context: User is currently in an onboarding flow]"

        if self.provider == "keywords_ai":
            # Build Keywords AI request with caching
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 50,
            }

            # Add caching parameters if enabled
            if settings.keywords_ai_cache_enabled:
                kwargs["extra_body"] = {
                    "cache_enabled": True,
                    "cache_ttl": settings.keywords_ai_cache_ttl,
                    "cache_options": {
                        "cache_by_customer": settings.keywords_ai_cache_by_customer,
                    },
                }

            response = await self.client.chat.completions.create(**kwargs)
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
