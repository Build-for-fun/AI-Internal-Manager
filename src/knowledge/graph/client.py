"""Neo4j client for knowledge graph operations."""

import asyncio
from typing import Any
from uuid import uuid4

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import settings
from src.knowledge.graph.schema import (
    SCHEMA_CONSTRAINTS,
    SCHEMA_INDEXES,
    NodeLabels,
    RelationshipTypes,
)

logger = structlog.get_logger()


class Neo4jClient:
    """Async Neo4j client for knowledge graph operations."""

    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Connect to Neo4j database."""
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
        await self.verify_connectivity()
        await self._init_schema()
        logger.info("Neo4j connected and schema initialized")

    async def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connectivity."""
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        await self._driver.verify_connectivity()
        return True

    async def _init_schema(self) -> None:
        """Initialize database schema with constraints and indexes."""
        async with self._driver.session() as session:
            for constraint in SCHEMA_CONSTRAINTS:
                try:
                    await session.run(constraint)
                except Exception as e:
                    logger.warning("Constraint creation skipped", constraint=constraint, error=str(e))

            for index in SCHEMA_INDEXES:
                try:
                    await session.run(index)
                except Exception as e:
                    logger.warning("Index creation skipped", index=index, error=str(e))

    @property
    def driver(self) -> AsyncDriver:
        """Get the Neo4j driver."""
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized. Call connect() first.")
        return self._driver

    # Node operations

    async def create_node(
        self,
        label: NodeLabels,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new node with the given label and properties."""
        if "id" not in properties:
            properties["id"] = str(uuid4())

        query = f"""
        CREATE (n:{label.value} $props)
        SET n.created_at = datetime()
        SET n.updated_at = datetime()
        RETURN n
        """

        async with self.driver.session() as session:
            result = await session.run(query, props=properties)
            record = await result.single()
            return dict(record["n"]) if record else {}

    async def get_node(self, node_id: str, label: NodeLabels | None = None) -> dict[str, Any] | None:
        """Get a node by ID."""
        if label:
            query = f"MATCH (n:{label.value} {{id: $id}}) RETURN n"
        else:
            query = "MATCH (n {id: $id}) RETURN n"

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id)
            record = await result.single()
            return dict(record["n"]) if record else None

    async def update_node(
        self,
        node_id: str,
        properties: dict[str, Any],
        label: NodeLabels | None = None,
    ) -> dict[str, Any] | None:
        """Update a node's properties."""
        if label:
            query = f"""
            MATCH (n:{label.value} {{id: $id}})
            SET n += $props
            SET n.updated_at = datetime()
            RETURN n
            """
        else:
            query = """
            MATCH (n {id: $id})
            SET n += $props
            SET n.updated_at = datetime()
            RETURN n
            """

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id, props=properties)
            record = await result.single()
            return dict(record["n"]) if record else None

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships."""
        query = """
        MATCH (n {id: $id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id)
            record = await result.single()
            return record["deleted"] > 0 if record else False

    # Relationship operations

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipTypes,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between two nodes."""
        props = properties or {}
        if "id" not in props:
            props["id"] = str(uuid4())

        query = f"""
        MATCH (a {{id: $source_id}})
        MATCH (b {{id: $target_id}})
        CREATE (a)-[r:{rel_type.value} $props]->(b)
        SET r.created_at = datetime()
        RETURN r, a, b
        """

        async with self.driver.session() as session:
            result = await session.run(query, source_id=source_id, target_id=target_id, props=props)
            record = await result.single()
            if record:
                return {
                    "relationship": dict(record["r"]),
                    "source": dict(record["a"]),
                    "target": dict(record["b"]),
                }
            return {}

    async def get_relationships(
        self,
        node_id: str,
        rel_type: RelationshipTypes | None = None,
        direction: str = "both",  # "outgoing", "incoming", "both"
    ) -> list[dict[str, Any]]:
        """Get relationships for a node."""
        rel_pattern = f":{rel_type.value}" if rel_type else ""

        if direction == "outgoing":
            query = f"""
            MATCH (a {{id: $id}})-[r{rel_pattern}]->(b)
            RETURN r, b as other, 'outgoing' as direction
            """
        elif direction == "incoming":
            query = f"""
            MATCH (a {{id: $id}})<-[r{rel_pattern}]-(b)
            RETURN r, b as other, 'incoming' as direction
            """
        else:
            query = f"""
            MATCH (a {{id: $id}})-[r{rel_pattern}]-(b)
            RETURN r, b as other,
                   CASE WHEN startNode(r).id = $id THEN 'outgoing' ELSE 'incoming' END as direction
            """

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id)
            records = await result.data()
            return [
                {
                    "relationship": dict(r["r"]),
                    "other_node": dict(r["other"]),
                    "direction": r["direction"],
                }
                for r in records
            ]

    # Hierarchy operations

    async def get_hierarchy(
        self,
        root_id: str | None = None,
        max_depth: int = 4,
    ) -> list[dict[str, Any]]:
        """Get the textbook hierarchy starting from root or all departments."""
        if root_id:
            query = """
            MATCH path = (root {id: $root_id})-[:HAS_SUBDEPARTMENT|HAS_TOPIC|HAS_CONTEXT*0..$max_depth]->(child)
            RETURN path
            """
            params = {"root_id": root_id, "max_depth": max_depth}
        else:
            query = """
            MATCH (d:Department)
            OPTIONAL MATCH path = (d)-[:HAS_SUBDEPARTMENT|HAS_TOPIC|HAS_CONTEXT*0..$max_depth]->(child)
            RETURN d, collect(path) as paths
            """
            params = {"max_depth": max_depth}

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return records

    async def get_children(
        self,
        node_id: str,
        child_label: NodeLabels | None = None,
    ) -> list[dict[str, Any]]:
        """Get direct children of a node in the hierarchy."""
        if child_label:
            query = f"""
            MATCH (parent {{id: $id}})-[:HAS_SUBDEPARTMENT|HAS_TOPIC|HAS_CONTEXT]->(child:{child_label.value})
            RETURN child
            ORDER BY child.title
            """
        else:
            query = """
            MATCH (parent {id: $id})-[:HAS_SUBDEPARTMENT|HAS_TOPIC|HAS_CONTEXT]->(child)
            RETURN child, labels(child) as labels
            ORDER BY child.title
            """

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id)
            records = await result.data()
            return records

    async def get_path_to_root(self, node_id: str) -> list[dict[str, Any]]:
        """Get the path from a node to its root department."""
        query = """
        MATCH path = (node {id: $id})<-[:HAS_SUBDEPARTMENT|HAS_TOPIC|HAS_CONTEXT*]-(ancestor)
        WHERE ancestor:Department
        RETURN [n in nodes(path) | {id: n.id, title: n.title, labels: labels(n)}] as path
        ORDER BY length(path) DESC
        LIMIT 1
        """

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id)
            record = await result.single()
            return record["path"] if record else []

    # Full-text search

    async def fulltext_search(
        self,
        query_text: str,
        node_types: list[NodeLabels] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Perform full-text search on content nodes."""
        # Default to searching context and summary nodes
        if not node_types:
            indexes = ["context_content", "summary_content", "decision_content"]
        else:
            index_map = {
                NodeLabels.CONTEXT: "context_content",
                NodeLabels.SUMMARY: "summary_content",
                NodeLabels.DECISION: "decision_content",
            }
            indexes = [index_map[nt] for nt in node_types if nt in index_map]

        if not indexes:
            return []

        results = []
        async with self.driver.session() as session:
            for index in indexes:
                query = f"""
                CALL db.index.fulltext.queryNodes('{index}', $query_text)
                YIELD node, score
                RETURN node, score, labels(node) as labels
                ORDER BY score DESC
                LIMIT $limit
                """
                result = await session.run(query, query_text=query_text, limit=limit)
                records = await result.data()
                results.extend([
                    {
                        "node": dict(r["node"]),
                        "score": r["score"],
                        "labels": r["labels"],
                    }
                    for r in records
                ])

        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # Aggregation queries

    async def get_context_count_by_topic(self, topic_id: str) -> int:
        """Get the number of context nodes for a topic."""
        query = """
        MATCH (t:Topic {id: $topic_id})-[:HAS_CONTEXT]->(c:Context)
        RETURN count(c) as count
        """

        async with self.driver.session() as session:
            result = await session.run(query, topic_id=topic_id)
            record = await result.single()
            return record["count"] if record else 0

    async def get_recent_contexts(
        self,
        topic_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent context nodes, optionally filtered by topic."""
        if topic_id:
            query = """
            MATCH (t:Topic {id: $topic_id})-[:HAS_CONTEXT]->(c:Context)
            RETURN c
            ORDER BY c.created_at DESC
            LIMIT $limit
            """
            params = {"topic_id": topic_id, "limit": limit}
        else:
            query = """
            MATCH (c:Context)
            RETURN c
            ORDER BY c.created_at DESC
            LIMIT $limit
            """
            params = {"limit": limit}

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return [dict(r["c"]) for r in records]

    # Convenience methods for seeding and common operations

    async def create_or_update_node(
        self,
        node_type: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Create or update a node by ID."""
        node_id = properties.get("id")
        if not node_id:
            raise ValueError("Node properties must include 'id'")

        # Use compatible syntax for older Neo4j versions
        query = f"""
        MERGE (n:{node_type} {{id: $id}})
        SET n += $props
        SET n.updated_at = datetime()
        SET n.created_at = coalesce(n.created_at, datetime())
        RETURN n
        """

        async with self.driver.session() as session:
            result = await session.run(query, id=node_id, props=properties)
            record = await result.single()
            return dict(record["n"]) if record else {}

    async def create_relationship_by_type(
        self,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        relationship_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between nodes specified by type and ID."""
        props = properties or {}

        query = f"""
        MATCH (a:{from_type} {{id: $from_id}})
        MATCH (b:{to_type} {{id: $to_id}})
        MERGE (a)-[r:{relationship_type}]->(b)
        SET r += $props
        SET r.created_at = coalesce(r.created_at, datetime())
        RETURN r, a, b
        """

        async with self.driver.session() as session:
            result = await session.run(
                query, from_id=from_id, to_id=to_id, props=props
            )
            record = await result.single()
            if record:
                return {
                    "relationship": dict(record["r"]),
                    "source": dict(record["a"]),
                    "target": dict(record["b"]),
                }
            return {}

    async def get_department_hierarchy(self) -> list[dict[str, Any]]:
        """Get the full textbook hierarchy organized by department."""
        query = """
        MATCH (d:Department)
        OPTIONAL MATCH (d)-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment)
        OPTIONAL MATCH (sd)-[:HAS_TOPIC]->(t:Topic)
        OPTIONAL MATCH (t)-[:HAS_CONTEXT]->(c:Context)
        OPTIONAL MATCH (t)-[:HAS_SUMMARY]->(s:Summary)
        RETURN d, collect(DISTINCT sd) as subdepts,
               collect(DISTINCT t) as topics,
               collect(DISTINCT c) as contexts,
               collect(DISTINCT s) as summaries
        ORDER BY d.title
        """

        async with self.driver.session() as session:
            result = await session.run(query)
            records = await result.data()
            return records

    async def store_chat_context(
        self,
        department_id: str,
        topic_id: str,
        content: str,
        title: str,
        source_type: str = "chat",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store a chat context in the knowledge graph under a topic."""
        context_id = str(uuid4())
        properties = {
            "id": context_id,
            "title": title,
            "content": content,
            "source_type": source_type,
            "topic_id": topic_id,
            "department_id": department_id,
            **(metadata or {}),
        }

        # Create context node
        context = await self.create_node(NodeLabels.CONTEXT, properties)

        # Link to topic
        await self.create_relationship(
            topic_id,
            context_id,
            RelationshipTypes.HAS_CONTEXT,
        )

        return context


    # ============================================
    # Hybrid Knowledge Management (Tags & Cross-References)
    # ============================================

    async def create_tag(
        self,
        name: str,
        category: str = "general",
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Create or get a tag for cross-cutting concerns.

        Tags enable knowledge organization across the hierarchy.
        Examples: "security", "performance", "api-design", "onboarding"
        """
        # Normalize tag name (lowercase, hyphenated)
        normalized_name = name.lower().replace(" ", "-").replace("_", "-")

        query = """
        MERGE (t:Tag {name: $name})
        ON CREATE SET
            t.id = $id,
            t.title = $title,
            t.category = $category,
            t.description = $description,
            t.color = $color,
            t.created_at = datetime(),
            t.updated_at = datetime()
        ON MATCH SET
            t.updated_at = datetime()
        RETURN t
        """

        async with self.driver.session() as session:
            result = await session.run(
                query,
                name=normalized_name,
                id=str(uuid4()),
                title=name,
                category=category,
                description=description,
                color=color,
            )
            record = await result.single()
            return dict(record["t"]) if record else {}

    async def add_tags_to_node(
        self,
        node_id: str,
        tag_names: list[str],
    ) -> list[dict[str, Any]]:
        """Add multiple tags to a node (Context, Topic, or any other node).

        Creates tags if they don't exist.
        """
        results = []
        for tag_name in tag_names:
            # Ensure tag exists
            tag = await self.create_tag(tag_name)

            # Create HAS_TAG relationship
            query = """
            MATCH (n {id: $node_id})
            MATCH (t:Tag {name: $tag_name})
            MERGE (n)-[r:HAS_TAG]->(t)
            ON CREATE SET r.created_at = datetime()
            RETURN n, t, r
            """

            normalized_name = tag_name.lower().replace(" ", "-").replace("_", "-")
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    node_id=node_id,
                    tag_name=normalized_name,
                )
                record = await result.single()
                if record:
                    results.append({
                        "node": dict(record["n"]),
                        "tag": dict(record["t"]),
                    })

        return results

    async def get_node_tags(self, node_id: str) -> list[dict[str, Any]]:
        """Get all tags for a node."""
        query = """
        MATCH (n {id: $node_id})-[:HAS_TAG]->(t:Tag)
        RETURN t
        ORDER BY t.name
        """

        async with self.driver.session() as session:
            result = await session.run(query, node_id=node_id)
            records = await result.data()
            return [dict(r["t"]) for r in records]

    async def find_by_tags(
        self,
        tag_names: list[str],
        node_label: str | None = None,
        match_all: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Find nodes by tags, bypassing the hierarchy.

        Args:
            tag_names: List of tag names to search for
            node_label: Optional node label filter (e.g., "Context", "Topic")
            match_all: If True, node must have ALL tags. If False, ANY tag matches.
            limit: Maximum results to return
        """
        normalized_tags = [t.lower().replace(" ", "-").replace("_", "-") for t in tag_names]

        if match_all:
            # Node must have ALL specified tags
            label_filter = f":{node_label}" if node_label else ""
            query = f"""
            MATCH (n{label_filter})-[:HAS_TAG]->(t:Tag)
            WHERE t.name IN $tags
            WITH n, collect(DISTINCT t.name) as node_tags
            WHERE size([tag IN $tags WHERE tag IN node_tags]) = size($tags)
            RETURN n, node_tags as tags
            LIMIT $limit
            """
        else:
            # Node can have ANY of the specified tags
            label_filter = f":{node_label}" if node_label else ""
            query = f"""
            MATCH (n{label_filter})-[:HAS_TAG]->(t:Tag)
            WHERE t.name IN $tags
            WITH n, collect(DISTINCT t.name) as node_tags, count(DISTINCT t) as tag_count
            RETURN n, node_tags as tags
            ORDER BY tag_count DESC
            LIMIT $limit
            """

        async with self.driver.session() as session:
            result = await session.run(query, tags=normalized_tags, limit=limit)
            records = await result.data()
            return [{"node": dict(r["n"]), "tags": r["tags"]} for r in records]

    async def create_cross_reference(
        self,
        topic_id_1: str,
        topic_id_2: str,
        description: str | None = None,
        bidirectional: bool = True,
    ) -> dict[str, Any]:
        """Create a cross-reference between two topics.

        This enables navigation between related topics across the hierarchy.
        """
        query = """
        MATCH (t1:Topic {id: $topic_id_1})
        MATCH (t2:Topic {id: $topic_id_2})
        MERGE (t1)-[r:CROSS_REFERENCES]->(t2)
        ON CREATE SET
            r.id = $id,
            r.description = $description,
            r.created_at = datetime()
        RETURN t1, t2, r
        """

        async with self.driver.session() as session:
            result = await session.run(
                query,
                topic_id_1=topic_id_1,
                topic_id_2=topic_id_2,
                id=str(uuid4()),
                description=description,
            )
            record = await result.single()

            # Create reverse relationship if bidirectional
            if bidirectional:
                reverse_query = """
                MATCH (t1:Topic {id: $topic_id_1})
                MATCH (t2:Topic {id: $topic_id_2})
                MERGE (t2)-[r:CROSS_REFERENCES]->(t1)
                ON CREATE SET
                    r.id = $id,
                    r.description = $description,
                    r.created_at = datetime()
                RETURN r
                """
                await session.run(
                    reverse_query,
                    topic_id_1=topic_id_1,
                    topic_id_2=topic_id_2,
                    id=str(uuid4()),
                    description=description,
                )

            if record:
                return {
                    "topic_1": dict(record["t1"]),
                    "topic_2": dict(record["t2"]),
                    "relationship": dict(record["r"]),
                }
            return {}

    async def get_cross_references(self, topic_id: str) -> list[dict[str, Any]]:
        """Get all topics that cross-reference with a given topic."""
        query = """
        MATCH (t:Topic {id: $topic_id})-[r:CROSS_REFERENCES]-(other:Topic)
        OPTIONAL MATCH (other)<-[:HAS_TOPIC]-(sd:SubDepartment)<-[:HAS_SUBDEPARTMENT]-(d:Department)
        RETURN other, r.description as description, d.title as department, sd.title as subdepartment
        """

        async with self.driver.session() as session:
            result = await session.run(query, topic_id=topic_id)
            records = await result.data()
            return [
                {
                    "topic": dict(r["other"]),
                    "description": r["description"],
                    "department": r["department"],
                    "subdepartment": r["subdepartment"],
                }
                for r in records
            ]

    async def add_context_to_multiple_topics(
        self,
        context_id: str,
        topic_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Link a context to multiple topics (many-to-many).

        The first topic uses HAS_CONTEXT, additional topics use ALSO_IN.
        """
        results = []
        for i, topic_id in enumerate(topic_ids):
            rel_type = "HAS_CONTEXT" if i == 0 else "ALSO_IN"
            query = f"""
            MATCH (t:Topic {{id: $topic_id}})
            MATCH (c:Context {{id: $context_id}})
            MERGE (t)-[r:{rel_type}]->(c)
            ON CREATE SET r.created_at = datetime()
            RETURN t, c, r
            """

            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    topic_id=topic_id,
                    context_id=context_id,
                )
                record = await result.single()
                if record:
                    results.append({
                        "topic": dict(record["t"]),
                        "context": dict(record["c"]),
                        "relationship_type": rel_type,
                    })

        return results

    async def get_context_topics(self, context_id: str) -> list[dict[str, Any]]:
        """Get all topics a context belongs to (including ALSO_IN relationships)."""
        query = """
        MATCH (t:Topic)-[:HAS_CONTEXT|ALSO_IN]->(c:Context {id: $context_id})
        OPTIONAL MATCH (t)<-[:HAS_TOPIC]-(sd:SubDepartment)<-[:HAS_SUBDEPARTMENT]-(d:Department)
        RETURN t, d.title as department, sd.title as subdepartment
        """

        async with self.driver.session() as session:
            result = await session.run(query, context_id=context_id)
            records = await result.data()
            return [
                {
                    "topic": dict(r["t"]),
                    "department": r["department"],
                    "subdepartment": r["subdepartment"],
                }
                for r in records
            ]

    async def search_across_hierarchy(
        self,
        query_text: str,
        tags: list[str] | None = None,
        source_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search knowledge across the entire hierarchy.

        This bypasses the hierarchical navigation and searches directly,
        optionally filtering by tags and source types.
        """
        # Build filter conditions
        conditions = ["toLower(c.content) CONTAINS toLower($query) OR toLower(c.title) CONTAINS toLower($query)"]
        params: dict[str, Any] = {"query": query_text, "limit": limit}

        if source_types:
            conditions.append("c.source_type IN $source_types")
            params["source_types"] = source_types

        where_clause = " AND ".join(conditions)

        if tags:
            normalized_tags = [t.lower().replace(" ", "-").replace("_", "-") for t in tags]
            params["tags"] = normalized_tags
            query = f"""
            MATCH (c:Context)-[:HAS_TAG]->(tag:Tag)
            WHERE tag.name IN $tags AND ({where_clause})
            OPTIONAL MATCH (t:Topic)-[:HAS_CONTEXT|ALSO_IN]->(c)
            OPTIONAL MATCH (t)<-[:HAS_TOPIC]-(sd:SubDepartment)<-[:HAS_SUBDEPARTMENT]-(d:Department)
            WITH c, collect(DISTINCT tag.name) as tags, collect(DISTINCT t.title) as topics,
                 collect(DISTINCT d.title) as departments
            RETURN c, tags, topics, departments
            ORDER BY c.importance DESC, c.created_at DESC
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (c:Context)
            WHERE {where_clause}
            OPTIONAL MATCH (c)-[:HAS_TAG]->(tag:Tag)
            OPTIONAL MATCH (t:Topic)-[:HAS_CONTEXT|ALSO_IN]->(c)
            OPTIONAL MATCH (t)<-[:HAS_TOPIC]-(sd:SubDepartment)<-[:HAS_SUBDEPARTMENT]-(d:Department)
            WITH c, collect(DISTINCT tag.name) as tags, collect(DISTINCT t.title) as topics,
                 collect(DISTINCT d.title) as departments
            RETURN c, tags, topics, departments
            ORDER BY c.importance DESC, c.created_at DESC
            LIMIT $limit
            """

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return [
                {
                    "context": dict(r["c"]),
                    "tags": r["tags"],
                    "topics": r["topics"],
                    "departments": r["departments"],
                }
                for r in records
            ]

    async def get_all_tags(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get all tags, optionally filtered by category."""
        if category:
            query = """
            MATCH (t:Tag {category: $category})
            OPTIONAL MATCH (n)-[:HAS_TAG]->(t)
            RETURN t, count(n) as usage_count
            ORDER BY usage_count DESC, t.name
            """
            params = {"category": category}
        else:
            query = """
            MATCH (t:Tag)
            OPTIONAL MATCH (n)-[:HAS_TAG]->(t)
            RETURN t, count(n) as usage_count
            ORDER BY usage_count DESC, t.name
            """
            params = {}

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return [
                {
                    "tag": dict(r["t"]),
                    "usage_count": r["usage_count"],
                }
                for r in records
            ]


# Singleton instance
neo4j_client = Neo4jClient()
