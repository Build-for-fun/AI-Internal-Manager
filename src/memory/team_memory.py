"""Team-level memory.

Stores team-specific information:
- Team norms and practices
- Decisions and their context
- Communication patterns
- Project history
"""

from datetime import datetime
from typing import Any

import structlog

from src.knowledge.indexing.embedder import embedder

logger = structlog.get_logger()


class TeamMemory:
    """Long-term memory manager for teams."""

    COLLECTION = "team_memory"

    async def store_norm(
        self,
        team_id: str,
        norm_type: str,
        description: str,
        rationale: str | None = None,
    ) -> str:
        """Store a team norm or practice."""
        text = f"Team norm ({norm_type}): {description}"
        if rationale:
            text += f". Rationale: {rationale}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "team_id": team_id,
                "type": "norm",
                "norm_type": norm_type,
                "description": description,
                "rationale": rationale,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_decision(
        self,
        team_id: str,
        decision: str,
        context: str,
        participants: list[str] | None = None,
        alternatives: list[str] | None = None,
    ) -> str:
        """Store a team decision."""
        text = f"Decision: {decision}\nContext: {context}"
        if alternatives:
            text += f"\nAlternatives considered: {', '.join(alternatives)}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "team_id": team_id,
                "type": "decision",
                "decision": decision,
                "context": context,
                "participants": participants or [],
                "alternatives": alternatives or [],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_project_context(
        self,
        team_id: str,
        project_id: str,
        project_name: str,
        description: str,
        status: str,
        key_learnings: list[str] | None = None,
    ) -> str:
        """Store project context for the team."""
        text = f"Project: {project_name}\nDescription: {description}\nStatus: {status}"
        if key_learnings:
            text += f"\nKey learnings: {', '.join(key_learnings)}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "team_id": team_id,
                "type": "project",
                "project_id": project_id,
                "project_name": project_name,
                "status": status,
                "key_learnings": key_learnings or [],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_communication_pattern(
        self,
        team_id: str,
        pattern_type: str,
        description: str,
        frequency: str,
    ) -> str:
        """Store team communication pattern."""
        text = f"Communication pattern ({pattern_type}): {description}. Frequency: {frequency}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "team_id": team_id,
                "type": "communication_pattern",
                "pattern_type": pattern_type,
                "frequency": frequency,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def get_team_context(
        self,
        team_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get relevant team context for a query."""
        return await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=limit,
            filters={"team_id": team_id},
        )

    async def get_norms(
        self,
        team_id: str,
        norm_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get team norms."""
        query = f"team norms {norm_type or ''}"
        results = await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=20,
            filters={"team_id": team_id, "type": "norm"},
        )

        if norm_type:
            results = [r for r in results if r.get("norm_type") == norm_type]

        return results

    async def get_decisions(
        self,
        team_id: str,
        topic: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get team decisions."""
        query = f"team decisions {topic or ''}"
        return await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=limit,
            filters={"team_id": team_id, "type": "decision"},
        )

    async def get_project_history(
        self,
        team_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get team's project history."""
        results = await embedder.search(
            collection=self.COLLECTION,
            query="team projects",
            limit=50,
            filters={"team_id": team_id, "type": "project"},
        )

        if status:
            results = [r for r in results if r.get("status") == status]

        return results

    async def clear_team_memory(self, team_id: str) -> int:
        """Clear all memory for a team."""
        return await embedder.delete_by_filter(
            collection=self.COLLECTION,
            filters={"team_id": team_id},
        )


# Singleton instance
team_memory = TeamMemory()
