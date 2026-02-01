"""Organization-level memory.

Stores organization-wide information:
- Company policies and procedures
- Best practices
- Cross-team knowledge
- Strategic initiatives
"""

from datetime import datetime
from typing import Any

import structlog

from src.knowledge.indexing.embedder import embedder

logger = structlog.get_logger()


class OrgMemory:
    """Long-term memory manager for organization-wide knowledge."""

    COLLECTION = "org_memory"

    async def store_policy(
        self,
        policy_type: str,
        title: str,
        content: str,
        department: str | None = None,
        effective_date: str | None = None,
    ) -> str:
        """Store an organizational policy."""
        text = f"Policy ({policy_type}): {title}\n{content}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "type": "policy",
                "policy_type": policy_type,
                "title": title,
                "department": department,
                "effective_date": effective_date,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_best_practice(
        self,
        category: str,
        title: str,
        description: str,
        examples: list[str] | None = None,
        source_team: str | None = None,
    ) -> str:
        """Store a best practice."""
        text = f"Best Practice ({category}): {title}\n{description}"
        if examples:
            text += f"\nExamples: {', '.join(examples)}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "type": "best_practice",
                "category": category,
                "title": title,
                "examples": examples or [],
                "source_team": source_team,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_initiative(
        self,
        name: str,
        description: str,
        status: str,
        owners: list[str] | None = None,
        departments: list[str] | None = None,
    ) -> str:
        """Store a strategic initiative."""
        text = f"Initiative: {name}\nDescription: {description}\nStatus: {status}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "type": "initiative",
                "name": name,
                "status": status,
                "owners": owners or [],
                "departments": departments or [],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_cross_team_knowledge(
        self,
        title: str,
        content: str,
        teams: list[str],
        knowledge_type: str,  # "integration", "dependency", "shared_resource"
    ) -> str:
        """Store cross-team knowledge."""
        text = f"Cross-team knowledge ({knowledge_type}): {title}\n{content}\nTeams: {', '.join(teams)}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "type": "cross_team",
                "knowledge_type": knowledge_type,
                "title": title,
                "teams": teams,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def store_faq(
        self,
        question: str,
        answer: str,
        category: str,
        tags: list[str] | None = None,
    ) -> str:
        """Store a frequently asked question."""
        text = f"FAQ ({category})\nQ: {question}\nA: {answer}"

        return await embedder.store_embedding(
            collection=self.COLLECTION,
            text=text,
            metadata={
                "type": "faq",
                "category": category,
                "question": question,
                "answer": answer,
                "tags": tags or [],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search organization memory."""
        filters = {}
        if memory_type:
            filters["type"] = memory_type

        return await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=limit,
            filters=filters if filters else None,
        )

    async def get_policies(
        self,
        policy_type: str | None = None,
        department: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get organizational policies."""
        query = f"organizational policies {policy_type or ''} {department or ''}"
        results = await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=50,
            filters={"type": "policy"},
        )

        if policy_type:
            results = [r for r in results if r.get("policy_type") == policy_type]
        if department:
            results = [r for r in results if r.get("department") == department]

        return results

    async def get_best_practices(
        self,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get best practices."""
        query = f"best practices {category or ''}"
        results = await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=50,
            filters={"type": "best_practice"},
        )

        if category:
            results = [r for r in results if r.get("category") == category]

        return results

    async def get_initiatives(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get strategic initiatives."""
        results = await embedder.search(
            collection=self.COLLECTION,
            query="strategic initiatives",
            limit=50,
            filters={"type": "initiative"},
        )

        if status:
            results = [r for r in results if r.get("status") == status]

        return results

    async def search_faqs(
        self,
        query: str,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search FAQs."""
        filters = {"type": "faq"}
        if category:
            filters["category"] = category

        return await embedder.search(
            collection=self.COLLECTION,
            query=query,
            limit=limit,
            filters=filters,
        )


# Singleton instance
org_memory = OrgMemory()
