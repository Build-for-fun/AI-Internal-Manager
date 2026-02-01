"""User-level long-term memory.

Stores user-specific information:
- Preferences and settings
- Interaction history patterns
- Personal knowledge context
- Expertise areas
"""

from datetime import datetime
from typing import Any

import structlog

from src.knowledge.indexing.embedder import embedder

logger = structlog.get_logger()


class UserMemory:
    """Long-term memory manager for individual users."""

    COLLECTION = "user_memory"

    async def store_preference(
        self,
        user_id: str,
        preference_type: str,
        value: Any,
        context: str | None = None,
    ) -> str:
        """Store a user preference."""
        text = f"User preference: {preference_type} = {value}"
        if context:
            text += f". Context: {context}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "user_id": user_id,
                "type": "preference",
                "preference_type": preference_type,
                "value": str(value),
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_interaction(
        self,
        user_id: str,
        query: str,
        response_summary: str,
        topics: list[str] | None = None,
        satisfaction: float | None = None,
    ) -> str:
        """Store an interaction for learning user patterns."""
        text = f"Query: {query}\nResponse: {response_summary}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "user_id": user_id,
                "type": "interaction",
                "topics": topics or [],
                "satisfaction": satisfaction,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_expertise(
        self,
        user_id: str,
        area: str,
        level: str,  # "beginner", "intermediate", "expert"
        evidence: str | None = None,
    ) -> str:
        """Store user expertise area."""
        text = f"User expertise in {area}: {level}"
        if evidence:
            text += f". Evidence: {evidence}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "user_id": user_id,
                "type": "expertise",
                "area": area,
                "level": level,
                "evidence": evidence,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def get_user_context(
        self,
        user_id: str,
        query: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get relevant user context for a query.

        If no query provided, returns recent memories.
        """
        if query:
            return await embedder.search(
                collection=self.COLLECTION,
                query=query,
                limit=limit,
                filters={"user_id": user_id},
            )

        # Return recent preferences and expertise
        results = await embedder.search(
            collection=self.COLLECTION,
            query="user preferences and expertise",
            limit=limit,
            filters={"user_id": user_id},
        )
        return results

    async def get_preferences(
        self,
        user_id: str,
        preference_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get user preferences."""
        query = f"user preferences {preference_type or ''}"
        results = await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=20,
            filters={"user_id": user_id, "type": "preference"},
        )

        if preference_type:
            results = [r for r in results if r.get("preference_type") == preference_type]

        return results

    async def get_interaction_history(
        self,
        user_id: str,
        topic: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get user's interaction history."""
        query = f"user interactions {topic or ''}"
        return await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=limit,
            filters={"user_id": user_id, "type": "interaction"},
        )

    async def get_expertise_areas(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Get user's expertise areas."""
        return await embedder.search(
            collection=self.COLLECTION,
            query="user expertise areas",
            limit=20,
            filters={"user_id": user_id, "type": "expertise"},
        )

    async def clear_user_memory(self, user_id: str) -> int:
        """Clear all memory for a user."""
        return await embedder.delete_by_filter(
            collection=self.COLLECTION,
            filters={"user_id": user_id},
        )


# Singleton instance
user_memory = UserMemory()
