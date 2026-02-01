"""Knowledge agent for retrieval and synthesis."""

from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.agents.knowledge.retrieval import hybrid_retriever
from src.config import settings
from src.mcp.registry import mcp_registry

logger = structlog.get_logger()


class KnowledgeAgent(BaseAgent):
    """Agent specialized in knowledge retrieval and synthesis.

    This agent:
    1. Retrieves relevant information from the knowledge graph and vectors
    2. Uses MCP tools to fetch live data from Jira, GitHub, Slack
    3. Synthesizes information into a coherent response
    4. Provides sources for transparency
    """

    def __init__(self):
        super().__init__(
            name="knowledge",
            description="Retrieves and synthesizes knowledge from company sources",
        )
        # Get relevant tools
        self._tools = mcp_registry.get_tools_for_agent("knowledge")

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a knowledge query.

        Steps:
        1. Retrieve relevant context from knowledge base
        2. Determine if additional tool calls are needed
        3. Generate a grounded response
        """
        # Get user context
        user_id = context.get("user_id", "")
        memory_context = context.get("memory_context", {})

        # Retrieve relevant knowledge
        retrieved_docs = await hybrid_retriever.retrieve(
            query=query,
            top_k=10,
            include_summaries=True,
        )

        # Format retrieved context
        knowledge_context = self._format_retrieved_docs(retrieved_docs)

        # Build system prompt
        system = f"""You are a knowledgeable AI assistant for an internal company system.
Your role is to answer questions about company processes, documentation, projects, and decisions.

IMPORTANT GUIDELINES:
1. Base your answers on the provided context when possible.
2. If the context doesn't contain relevant information, you may use your general knowledge to assist, but MUST explicitly state that this information comes from general knowledge and not the company's internal knowledge base.
3. When referencing information, be specific about the source.
4. If you're uncertain, express that uncertainty.
4. Be concise but thorough.
5. Use formatting (bullet points, headers) when helpful.

RESPONSE FORMAT:
- Use clear Markdown with headings.
- Start with a brief summary (1-2 sentences).
- Prefer bullet points for steps or lists.
- Include a "Sources" section when citing documents.
- Keep responses structured and scannable.

CONTEXT FROM KNOWLEDGE BASE:
{knowledge_context}

MEMORY CONTEXT:
{self._format_memory_context(memory_context)}
"""

        # Build messages
        messages = context.get("messages", [])
        messages.append({"role": "user", "content": query})

        # Run with potential tool use
        result = await self._run_with_tools(
            messages=messages,
            system=system,
            max_iterations=3,
        )

        # Extract sources from retrieved docs
        sources = [
            {
                "id": doc.get("id"),
                "title": doc.get("title", "Untitled"),
                "type": doc.get("node_type", doc.get("source", "unknown")),
                "url": doc.get("source_url"),
                "score": doc.get("score", 0),
            }
            for doc in retrieved_docs[:5]  # Top 5 sources
        ]

        return {
            "response": result["response"],
            "sources": sources,
            "tool_calls": result.get("tool_calls", []),
            "metadata": {
                "retrieved_count": len(retrieved_docs),
                "usage": result.get("usage", {}),
            },
        }

    def _format_retrieved_docs(self, docs: list[dict[str, Any]]) -> str:
        """Format retrieved documents for the prompt."""
        if not docs:
            return "No relevant documents found in the knowledge base."

        formatted = []
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", "Untitled")
            content = doc.get("text", doc.get("content", ""))
            source = doc.get("source", "unknown")
            node_type = doc.get("node_type", "")

            # Truncate long content
            if len(content) > 500:
                content = content[:500] + "..."

            formatted.append(f"""
[Document {i}]
Title: {title}
Type: {node_type or source}
Content: {content}
""")

        return "\n".join(formatted)

    def _format_memory_context(self, memory: dict[str, Any]) -> str:
        """Format memory context for the prompt."""
        if not memory:
            return "No additional context from memory."

        parts = []

        # User preferences
        if memory.get("user"):
            user_items = memory["user"][:2]
            if user_items:
                parts.append("User preferences: " + "; ".join(
                    item.get("text", "")[:100] for item in user_items
                ))

        # Team context
        if memory.get("team"):
            team_items = memory["team"][:2]
            if team_items:
                parts.append("Team context: " + "; ".join(
                    item.get("text", "")[:100] for item in team_items
                ))

        # Org context
        if memory.get("org"):
            org_items = memory["org"][:2]
            if org_items:
                parts.append("Organization: " + "; ".join(
                    item.get("text", "")[:100] for item in org_items
                ))

        return "\n".join(parts) if parts else "No additional context from memory."

    async def get_topic_summary(
        self,
        topic_id: str,
    ) -> dict[str, Any]:
        """Get a summary for a specific topic."""
        from src.knowledge.graph.client import neo4j_client

        # Get topic and its contexts
        topic = await neo4j_client.get_node(topic_id)
        if not topic:
            return {"error": "Topic not found"}

        # Get recent contexts
        contexts = await neo4j_client.get_recent_contexts(topic_id=topic_id, limit=20)

        # Get summaries
        async with neo4j_client.driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Topic {id: $topic_id})-[:HAS_SUMMARY]->(s:Summary)
                RETURN s
                ORDER BY s.period_end DESC
                LIMIT 1
                """,
                topic_id=topic_id,
            )
            summary_record = await result.single()

        summary = dict(summary_record["s"]) if summary_record else None

        return {
            "topic": topic,
            "recent_contexts": contexts[:5],
            "latest_summary": summary,
        }


# Singleton instance
knowledge_agent = KnowledgeAgent()
