"""Hybrid retrieval for knowledge agent.

Combines:
- Vector search (semantic similarity)
- Graph traversal (structural relationships)
- Full-text search (keyword matching)
"""

from typing import Any

import structlog

from src.knowledge.graph.client import neo4j_client
from src.knowledge.indexing.embedder import embedder

logger = structlog.get_logger()


class HybridRetriever:
    """Hybrid retrieval combining vector, graph, and full-text search."""

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        department: str | None = None,
        include_summaries: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents using hybrid search.

        Combines:
        1. Vector search for semantic similarity
        2. Full-text search for keyword matching
        3. Graph traversal for related contexts

        Results are re-ranked based on combined scores.
        """
        results = []

        # 1. Vector search on knowledge collection
        try:
            vector_results = await embedder.search(
                collection="knowledge",
                query=query,
                limit=top_k * 2,
                filters={"department": department} if department else None,
            )
            for r in vector_results:
                r["source"] = "vector"
                r["score"] = r.get("score", 0) * 1.0  # Base weight
            results.extend(vector_results)
        except Exception as e:
            logger.warning("Vector search failed", error=str(e))

        # 2. Full-text search on graph
        try:
            text_results = await neo4j_client.fulltext_search(
                query_text=query,
                limit=top_k,
            )
            for r in text_results:
                node = r.get("node", {})
                results.append({
                    "id": node.get("id"),
                    "text": node.get("content", node.get("title", "")),
                    "title": node.get("title"),
                    "node_type": r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown",
                    "source": "fulltext",
                    "score": r.get("score", 0) * 0.8,  # Slightly lower weight
                    "source_url": node.get("source_url"),
                })
        except Exception as e:
            logger.warning("Full-text search failed", error=str(e))

        # 3. Get summaries if requested
        if include_summaries:
            try:
                summary_results = await self._get_relevant_summaries(query)
                for r in summary_results:
                    r["source"] = "summary"
                    r["score"] = r.get("score", 0) * 0.9  # Summaries are valuable
                results.extend(summary_results)
            except Exception as e:
                logger.warning("Summary search failed", error=str(e))

        # Deduplicate by ID
        seen_ids = set()
        unique_results = []
        for r in results:
            rid = r.get("id")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                unique_results.append(r)

        # Sort by score
        unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return unique_results[:top_k]

    async def _get_relevant_summaries(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get relevant summaries from the knowledge graph."""
        # Search summaries in the graph
        cypher = """
        CALL db.index.fulltext.queryNodes('summary_content', $query)
        YIELD node, score
        WHERE score > 0.5
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """

        try:
            async with neo4j_client.driver.session() as session:
                result = await session.run(cypher, query=query, limit=limit)
                records = await result.data()

                return [
                    {
                        "id": r["node"]["id"],
                        "text": r["node"].get("content", ""),
                        "title": r["node"].get("title", ""),
                        "node_type": "Summary",
                        "score": r["score"],
                        "period_start": r["node"].get("period_start"),
                        "period_end": r["node"].get("period_end"),
                    }
                    for r in records
                ]
        except Exception:
            return []

    async def get_context_for_node(
        self,
        node_id: str,
        include_path: bool = True,
        include_related: bool = True,
    ) -> dict[str, Any]:
        """Get full context for a specific node.

        Includes:
        - The node itself
        - Path to root (hierarchy)
        - Related nodes through relationships
        """
        result = {}

        # Get the node
        node = await neo4j_client.get_node(node_id)
        if not node:
            return result

        result["node"] = node

        # Get path to root
        if include_path:
            path = await neo4j_client.get_path_to_root(node_id)
            result["path"] = path

        # Get related nodes
        if include_related:
            relationships = await neo4j_client.get_relationships(node_id)
            result["related"] = relationships

        return result

    async def expand_context(
        self,
        node_ids: list[str],
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Expand context by traversing relationships from given nodes.

        This is useful for adding related context to improve response quality.
        """
        expanded = []

        for node_id in node_ids:
            # Get immediate relationships
            relationships = await neo4j_client.get_relationships(node_id)

            for rel in relationships:
                other_node = rel.get("other_node", {})
                if other_node:
                    expanded.append({
                        "id": other_node.get("id"),
                        "title": other_node.get("title"),
                        "content": other_node.get("content"),
                        "relationship": rel.get("relationship", {}).get("type"),
                        "from_node": node_id,
                    })

        return expanded


# Singleton instance
hybrid_retriever = HybridRetriever()
