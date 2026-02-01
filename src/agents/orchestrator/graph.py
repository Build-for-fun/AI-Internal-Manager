"""LangGraph state machine for the orchestrator agent.

This module defines the state graph that manages conversation flow
and routes between specialized agents.
"""

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.orchestrator.intents import Intent, intent_classifier


class ConversationState(TypedDict):
    """State for the conversation graph.

    This state is passed between nodes and persisted for each conversation.
    """

    # Message history (kept as plain dicts for compatibility with LLM APIs)
    messages: list[dict[str, Any]]

    # Current query being processed
    current_query: str

    # Classified intent
    intent: Intent | None

    # Intent classification confidence
    intent_confidence: float

    # Active agent handling the query
    active_agent: str | None

    # User information
    user_id: str
    user_name: str | None
    user_role: str | None
    user_department: str | None
    user_team: str | None

    # Conversation metadata
    conversation_id: str
    conversation_type: str

    # Context from memory
    memory_context: dict[str, Any]

    # Response being built
    response: str | None
    sources: list[dict[str, Any]] | None

    # Error state
    error: str | None


async def classify_intent_node(state: ConversationState) -> dict[str, Any]:
    """Node that classifies the user's intent."""
    query = state["current_query"]

    # Build context for classification, including message history for follow-ups
    context = {
        "is_new_employee": state.get("conversation_type") == "onboarding",
        "current_flow": state.get("active_agent"),
        "messages": state.get("messages", []),  # Include history for follow-up context
    }

    intent, confidence = await intent_classifier.classify(query, context)

    return {
        "intent": intent,
        "intent_confidence": confidence,
    }


def route_by_intent(state: ConversationState) -> Literal["knowledge", "onboarding", "team_analysis", "evaluator", "direct_response", "clarification"]:
    """Route to the appropriate agent based on intent."""
    intent = state.get("intent")

    if intent == Intent.KNOWLEDGE:
        return "knowledge"
    elif intent == Intent.ONBOARDING:
        return "onboarding"
    elif intent == Intent.TEAM_ANALYSIS:
        return "team_analysis"
    elif intent == Intent.EVALUATOR:
        return "evaluator"
    elif intent == Intent.DIRECT_RESPONSE:
        return "direct_response"
    else:
        return "clarification"


async def knowledge_agent_node(state: ConversationState) -> dict[str, Any]:
    """Node that invokes the knowledge agent."""
    from src.agents.knowledge.agent import knowledge_agent

    result = await knowledge_agent.process(
        query=state["current_query"],
        context={
            "user_id": state["user_id"],
            "memory_context": state.get("memory_context", {}),
            "messages": state.get("messages", []),
        },
    )

    return {
        "response": result["response"],
        "sources": result.get("sources"),
        "active_agent": "knowledge",
    }


async def onboarding_agent_node(state: ConversationState) -> dict[str, Any]:
    """Node that invokes the onboarding agent."""
    from src.agents.onboarding.agent import onboarding_agent

    result = await onboarding_agent.process(
        query=state["current_query"],
        context={
            "user_id": state["user_id"],
            "user_name": state.get("user_name"),
            "user_role": state.get("user_role"),
            "user_department": state.get("user_department"),
            "memory_context": state.get("memory_context", {}),
            "messages": state.get("messages", []),
        },
    )

    return {
        "response": result["response"],
        "sources": result.get("sources"),
        "active_agent": "onboarding",
    }


async def team_analysis_agent_node(state: ConversationState) -> dict[str, Any]:
    """Node that invokes the team analysis agent."""
    from src.agents.team_analysis.agent import team_analysis_agent

    result = await team_analysis_agent.process(
        query=state["current_query"],
        context={
            "user_id": state["user_id"],
            "user_team": state.get("user_team"),
            "memory_context": state.get("memory_context", {}),
            "messages": state.get("messages", []),
        },
    )

    return {
        "response": result["response"],
        "sources": result.get("sources"),
        "active_agent": "team_analysis",
    }


async def evaluator_agent_node(state: ConversationState) -> dict[str, Any]:
    """Node that invokes the evaluator agent."""
    from src.agents.evaluator.agent import evaluator_agent

    result = await evaluator_agent.process(
        query=state["current_query"],
        context={
            "user_id": state["user_id"],
            "memory_context": state.get("memory_context", {}),
            "messages": state.get("messages", []),
        },
    )

    return {
        "response": result["response"],
        "sources": result.get("sources"),
        "active_agent": "evaluator",
    }


async def direct_response_node(state: ConversationState) -> dict[str, Any]:
    """Node for simple, direct responses."""
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI

    from src.config import settings

    query = state["current_query"]
    user_name = state.get("user_name", "there")
    system_prompt = (
        "You are a friendly AI assistant for internal company use. "
        f"The user's name is {user_name}. Keep responses brief and friendly.\n\n"
        "RESPONSE FORMAT:\n"
        "- Use clear Markdown with headings when helpful.\n"
        "- Start with a brief summary (1-2 sentences).\n"
        "- Prefer bullets for lists or steps.\n"
        "- Keep responses structured and scannable."
    )

    if settings.llm_provider == "keywords_ai":
        client = AsyncOpenAI(
            api_key=settings.keywords_ai_api_key.get_secret_value(),
            base_url=settings.keywords_ai_base_url,
        )

        # Build request with caching parameters
        kwargs: dict[str, Any] = {
            "model": settings.keywords_ai_default_model,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
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

        response = await client.chat.completions.create(**kwargs)
        response_text = response.choices[0].message.content
    else:
        client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
        response = await client.messages.create(
            model=settings.anthropic_fast_model,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": query}],
        )
        response_text = response.content[0].text

    return {
        "response": response_text,
        "active_agent": "direct_response",
    }


async def clarification_node(state: ConversationState) -> dict[str, Any]:
    """Node that asks for clarification."""
    return {
        "response": (
            "## Clarification Needed\n"
            "I want to help, but I need a bit more detail.\n\n"
            "**Could you clarify one of these?**\n"
            "- The specific team, project, or timeframe\n"
            "- The exact metric or output you want\n"
            "- Any constraints or context to consider"
        ),
        "active_agent": "clarification",
    }


def create_orchestrator_graph() -> StateGraph:
    """Create the orchestrator state graph.

    The graph flow:
    1. classify_intent: Determine what kind of query this is
    2. Route to appropriate agent based on intent
    3. Agent processes and returns response
    """
    # Create the graph
    graph = StateGraph(ConversationState)

    # Add nodes
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("knowledge", knowledge_agent_node)
    graph.add_node("onboarding", onboarding_agent_node)
    graph.add_node("team_analysis", team_analysis_agent_node)
    graph.add_node("evaluator", evaluator_agent_node)
    graph.add_node("direct_response", direct_response_node)
    graph.add_node("clarification", clarification_node)

    # Set entry point
    graph.set_entry_point("classify_intent")

    # Add conditional routing
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "knowledge": "knowledge",
            "onboarding": "onboarding",
            "team_analysis": "team_analysis",
            "evaluator": "evaluator",
            "direct_response": "direct_response",
            "clarification": "clarification",
        },
    )

    # All agent nodes lead to END
    graph.add_edge("knowledge", END)
    graph.add_edge("onboarding", END)
    graph.add_edge("team_analysis", END)
    graph.add_edge("evaluator", END)
    graph.add_edge("direct_response", END)
    graph.add_edge("clarification", END)

    return graph


# Compile the graph
orchestrator_graph = create_orchestrator_graph().compile()
