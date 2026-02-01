"""Memory manager that orchestrates all memory types."""

from typing import Any

import structlog

from src.memory.org_memory import org_memory
from src.memory.short_term import short_term_memory
from src.memory.team_memory import team_memory
from src.memory.user_memory import user_memory

logger = structlog.get_logger()


class MemoryManager:
    """Orchestrates memory retrieval across all memory types.

    Memory hierarchy (from most to least specific):
    1. Short-term: Current conversation context
    2. User: Individual preferences and history
    3. Team: Team norms and decisions
    4. Org: Company-wide policies and best practices
    """

    def __init__(self):
        self.short_term = short_term_memory
        self.user = user_memory
        self.team = team_memory
        self.org = org_memory

    async def get_context_for_query(
        self,
        query: str,
        user_id: str,
        team_id: str | None = None,
        conversation_id: str | None = None,
        include_short_term: bool = True,
        include_user: bool = True,
        include_team: bool = True,
        include_org: bool = True,
        limit_per_source: int = 5,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get relevant context from all memory sources.

        Returns a dictionary with context from each source.
        """
        context = {}

        # Short-term memory (conversation context)
        if include_short_term and conversation_id:
            messages = await self.short_term.get_messages(conversation_id)
            conv_context = await self.short_term.get_context(conversation_id)
            context["short_term"] = {
                "messages": messages[-limit_per_source:],
                "context": conv_context,
            }

        # User memory
        if include_user:
            user_context = await self.user.get_user_context(
                user_id=user_id,
                query=query,
                limit=limit_per_source,
            )
            context["user"] = user_context

        # Team memory
        if include_team and team_id:
            team_context = await self.team.get_team_context(
                team_id=team_id,
                query=query,
                limit=limit_per_source,
            )
            context["team"] = team_context

        # Org memory
        if include_org:
            org_context = await self.org.search(
                query=query,
                limit=limit_per_source,
            )
            context["org"] = org_context

        return context

    async def format_context_for_prompt(
        self,
        context: dict[str, Any],
        max_tokens: int = 2000,
    ) -> str:
        """Format retrieved context for LLM prompt.

        Prioritizes more specific memory (user > team > org).
        """
        sections = []

        # Short-term context
        if "short_term" in context:
            st = context["short_term"]
            if st.get("context"):
                sections.append(
                    f"Current Context:\n{self._format_dict(st['context'])}"
                )

        # User context
        if "user" in context and context["user"]:
            user_items = []
            for item in context["user"][:3]:
                user_items.append(f"- {item.get('text', '')[:200]}")
            if user_items:
                sections.append(f"User Context:\n" + "\n".join(user_items))

        # Team context
        if "team" in context and context["team"]:
            team_items = []
            for item in context["team"][:3]:
                team_items.append(f"- {item.get('text', '')[:200]}")
            if team_items:
                sections.append(f"Team Context:\n" + "\n".join(team_items))

        # Org context
        if "org" in context and context["org"]:
            org_items = []
            for item in context["org"][:3]:
                org_items.append(f"- {item.get('text', '')[:200]}")
            if org_items:
                sections.append(f"Organization Context:\n" + "\n".join(org_items))

        formatted = "\n\n".join(sections)

        # Truncate if too long (rough estimate of tokens)
        if len(formatted) > max_tokens * 4:
            formatted = formatted[: max_tokens * 4] + "\n[Context truncated...]"

        return formatted

    def _format_dict(self, d: dict[str, Any]) -> str:
        """Format a dictionary for display."""
        items = []
        for key, value in d.items():
            if isinstance(value, (dict, list)):
                continue  # Skip complex values
            items.append(f"- {key}: {value}")
        return "\n".join(items)

    async def store_conversation_memory(
        self,
        conversation_id: str,
        user_id: str,
        query: str,
        response: str,
        topics: list[str] | None = None,
    ) -> None:
        """Store conversation in both short-term and long-term memory.

        Short-term: Full messages for context
        Long-term: Summarized interaction for learning
        """
        # Store in short-term
        await self.short_term.store_message(
            conversation_id=conversation_id,
            role="user",
            content=query,
        )
        await self.short_term.store_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
        )

        # Store summarized interaction in user memory
        # Only store if the interaction seems significant
        if len(query) > 50 or topics:
            await self.user.store_interaction(
                user_id=user_id,
                query=query,
                response_summary=response[:500] if len(response) > 500 else response,
                topics=topics,
            )

    async def update_user_context(
        self,
        user_id: str,
        conversation_id: str,
        context_updates: dict[str, Any],
    ) -> None:
        """Update conversation context with user-specific information."""
        current_context = await self.short_term.get_context(conversation_id) or {}

        # Merge user info
        current_context["user_id"] = user_id
        current_context.update(context_updates)

        await self.short_term.set_context(conversation_id, current_context)

    async def get_onboarding_context(
        self,
        user_id: str,
        role: str | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Get context specifically for onboarding.

        Returns relevant policies, best practices, and team norms.
        """
        context = {}

        # Get relevant policies
        query = f"onboarding {role or ''} {department or ''}"
        context["policies"] = await self.org.get_policies(department=department)

        # Get best practices
        context["best_practices"] = await self.org.get_best_practices(
            category="onboarding" if not department else None
        )

        # Get relevant FAQs
        context["faqs"] = await self.org.search_faqs(
            query=query,
            limit=10,
        )

        return context

    async def get_analytics_context(
        self,
        team_id: str,
    ) -> dict[str, Any]:
        """Get context for team analytics.

        Returns team decisions, norms, and project history.
        """
        context = {}

        # Get team decisions
        context["decisions"] = await self.team.get_decisions(team_id=team_id, limit=10)

        # Get team norms
        context["norms"] = await self.team.get_norms(team_id=team_id)

        # Get project history
        context["projects"] = await self.team.get_project_history(team_id=team_id)

        return context


# Singleton instance
memory_manager = MemoryManager()
