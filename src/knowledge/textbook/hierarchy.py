"""Textbook hierarchy management.

The knowledge base is organized in a hierarchical "textbook" structure:

Department (e.g., "Engineering")
  └── SubDepartment (e.g., "Platform Team")
        └── Topic (e.g., "CI/CD Pipelines")
              └── Context (individual knowledge pieces from Jira, GitHub, Slack)
                    └── Summary (weekly/monthly consolidations)
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

from src.knowledge.graph.client import neo4j_client
from src.knowledge.graph.schema import NodeLabels, RelationshipTypes

logger = structlog.get_logger()


class HierarchyManager:
    """Manages the textbook-style knowledge hierarchy."""

    async def create_department(
        self,
        name: str,
        description: str | None = None,
        head_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new department (top-level node)."""
        properties = {
            "id": str(uuid4()),
            "title": name,
            "description": description,
            "head_id": head_id,
        }
        node = await neo4j_client.create_node(NodeLabels.DEPARTMENT, properties)
        logger.info("Created department", department_id=node.get("id"), name=name)
        return node

    async def create_subdepartment(
        self,
        department_id: str,
        name: str,
        description: str | None = None,
        lead_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a subdepartment under a department."""
        properties = {
            "id": str(uuid4()),
            "title": name,
            "description": description,
            "department_id": department_id,
            "lead_id": lead_id,
        }
        node = await neo4j_client.create_node(NodeLabels.SUB_DEPARTMENT, properties)

        # Create relationship
        await neo4j_client.create_relationship(
            department_id,
            node["id"],
            RelationshipTypes.HAS_SUBDEPARTMENT,
        )

        logger.info(
            "Created subdepartment",
            subdepartment_id=node.get("id"),
            department_id=department_id,
            name=name,
        )
        return node

    async def create_topic(
        self,
        subdepartment_id: str,
        name: str,
        description: str | None = None,
        importance: float = 0.5,
    ) -> dict[str, Any]:
        """Create a topic under a subdepartment."""
        properties = {
            "id": str(uuid4()),
            "title": name,
            "description": description,
            "sub_department_id": subdepartment_id,
            "importance": importance,
        }
        node = await neo4j_client.create_node(NodeLabels.TOPIC, properties)

        # Create relationship
        await neo4j_client.create_relationship(
            subdepartment_id,
            node["id"],
            RelationshipTypes.HAS_TOPIC,
        )

        logger.info(
            "Created topic",
            topic_id=node.get("id"),
            subdepartment_id=subdepartment_id,
            name=name,
        )
        return node

    async def add_context(
        self,
        topic_id: str,
        title: str,
        content: str,
        source_type: str,
        source_id: str,
        source_url: str | None = None,
        embedding_id: str | None = None,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a context (knowledge piece) to a topic."""
        properties = {
            "id": str(uuid4()),
            "title": title,
            "content": content,
            "source_type": source_type,
            "source_id": source_id,
            "source_url": source_url,
            "embedding_id": embedding_id,
            "importance": importance,
            "topic_id": topic_id,
            "metadata": metadata or {},
        }
        node = await neo4j_client.create_node(NodeLabels.CONTEXT, properties)

        # Create relationship
        await neo4j_client.create_relationship(
            topic_id,
            node["id"],
            RelationshipTypes.HAS_CONTEXT,
        )

        # Update topic's last_updated_context
        await neo4j_client.update_node(
            topic_id,
            {"last_updated_context": datetime.utcnow().isoformat()},
            NodeLabels.TOPIC,
        )

        logger.info(
            "Added context",
            context_id=node.get("id"),
            topic_id=topic_id,
            source_type=source_type,
        )
        return node

    async def get_hierarchy(
        self,
        department_id: str | None = None,
    ) -> dict[str, Any]:
        """Get the full hierarchy or for a specific department."""
        if department_id:
            return await self._get_department_hierarchy(department_id)
        return await self._get_full_hierarchy()

    async def _get_full_hierarchy(self) -> dict[str, Any]:
        """Get the complete textbook hierarchy."""
        query = """
        MATCH (d:Department)
        OPTIONAL MATCH (d)-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment)
        OPTIONAL MATCH (sd)-[:HAS_TOPIC]->(t:Topic)
        OPTIONAL MATCH (t)-[:HAS_CONTEXT]->(c:Context)
        WITH d, sd, t, count(c) as context_count
        RETURN d, sd, t, context_count
        ORDER BY d.title, sd.title, t.title
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(query)
            records = await result.data()

        # Build hierarchy structure
        departments = {}
        for record in records:
            dept = record.get("d")
            subdept = record.get("sd")
            topic = record.get("t")
            context_count = record.get("context_count", 0)

            if not dept:
                continue

            dept_id = dept["id"]
            if dept_id not in departments:
                departments[dept_id] = {
                    "id": dept_id,
                    "title": dept.get("title"),
                    "description": dept.get("description"),
                    "subdepartments": {},
                }

            if subdept:
                subdept_id = subdept["id"]
                if subdept_id not in departments[dept_id]["subdepartments"]:
                    departments[dept_id]["subdepartments"][subdept_id] = {
                        "id": subdept_id,
                        "title": subdept.get("title"),
                        "description": subdept.get("description"),
                        "topics": {},
                    }

                if topic:
                    topic_id = topic["id"]
                    departments[dept_id]["subdepartments"][subdept_id]["topics"][topic_id] = {
                        "id": topic_id,
                        "title": topic.get("title"),
                        "description": topic.get("description"),
                        "context_count": context_count,
                        "importance": topic.get("importance", 0.5),
                    }

        # Convert nested dicts to lists
        result_departments = []
        for dept in departments.values():
            dept["subdepartments"] = list(dept["subdepartments"].values())
            for subdept in dept["subdepartments"]:
                subdept["topics"] = list(subdept["topics"].values())
            result_departments.append(dept)

        total_nodes = sum(
            1 + len(d["subdepartments"]) + sum(len(sd["topics"]) for sd in d["subdepartments"])
            for d in result_departments
        )

        return {
            "departments": result_departments,
            "total_nodes": total_nodes,
        }

    async def _get_department_hierarchy(self, department_id: str) -> dict[str, Any]:
        """Get hierarchy for a specific department."""
        query = """
        MATCH (d:Department {id: $department_id})
        OPTIONAL MATCH (d)-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment)
        OPTIONAL MATCH (sd)-[:HAS_TOPIC]->(t:Topic)
        OPTIONAL MATCH (t)-[:HAS_CONTEXT]->(c:Context)
        WITH d, sd, t, count(c) as context_count
        RETURN d, sd, t, context_count
        ORDER BY sd.title, t.title
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(query, department_id=department_id)
            records = await result.data()

        if not records:
            return {}

        dept = records[0].get("d")
        if not dept:
            return {}

        department = {
            "id": dept["id"],
            "title": dept.get("title"),
            "description": dept.get("description"),
            "subdepartments": {},
        }

        for record in records:
            subdept = record.get("sd")
            topic = record.get("t")
            context_count = record.get("context_count", 0)

            if subdept:
                subdept_id = subdept["id"]
                if subdept_id not in department["subdepartments"]:
                    department["subdepartments"][subdept_id] = {
                        "id": subdept_id,
                        "title": subdept.get("title"),
                        "description": subdept.get("description"),
                        "topics": [],
                    }

                if topic:
                    department["subdepartments"][subdept_id]["topics"].append({
                        "id": topic["id"],
                        "title": topic.get("title"),
                        "description": topic.get("description"),
                        "context_count": context_count,
                        "importance": topic.get("importance", 0.5),
                    })

        department["subdepartments"] = list(department["subdepartments"].values())
        return department

    async def get_path_to_root(self, node_id: str) -> list[dict[str, Any]]:
        """Get the hierarchy path from a node to its root department."""
        return await neo4j_client.get_path_to_root(node_id)

    async def find_or_create_path(
        self,
        department_name: str,
        subdepartment_name: str | None = None,
        topic_name: str | None = None,
    ) -> dict[str, str]:
        """Find or create nodes along a hierarchy path.

        Returns the IDs of the nodes at each level.
        """
        result = {}

        # Find or create department
        query = "MATCH (d:Department {title: $name}) RETURN d"
        async with neo4j_client.driver.session() as session:
            dept_result = await session.run(query, name=department_name)
            dept_record = await dept_result.single()

        if dept_record:
            result["department_id"] = dept_record["d"]["id"]
        else:
            dept = await self.create_department(department_name)
            result["department_id"] = dept["id"]

        if not subdepartment_name:
            return result

        # Find or create subdepartment
        query = """
        MATCH (d:Department {id: $dept_id})-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment {title: $name})
        RETURN sd
        """
        async with neo4j_client.driver.session() as session:
            subdept_result = await session.run(
                query,
                dept_id=result["department_id"],
                name=subdepartment_name,
            )
            subdept_record = await subdept_result.single()

        if subdept_record:
            result["subdepartment_id"] = subdept_record["sd"]["id"]
        else:
            subdept = await self.create_subdepartment(
                result["department_id"],
                subdepartment_name,
            )
            result["subdepartment_id"] = subdept["id"]

        if not topic_name:
            return result

        # Find or create topic
        query = """
        MATCH (sd:SubDepartment {id: $subdept_id})-[:HAS_TOPIC]->(t:Topic {title: $name})
        RETURN t
        """
        async with neo4j_client.driver.session() as session:
            topic_result = await session.run(
                query,
                subdept_id=result["subdepartment_id"],
                name=topic_name,
            )
            topic_record = await topic_result.single()

        if topic_record:
            result["topic_id"] = topic_record["t"]["id"]
        else:
            topic = await self.create_topic(result["subdepartment_id"], topic_name)
            result["topic_id"] = topic["id"]

        return result

    async def get_contexts_for_topic(
        self,
        topic_id: str,
        limit: int = 50,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all context nodes for a topic."""
        if source_type:
            query = """
            MATCH (t:Topic {id: $topic_id})-[:HAS_CONTEXT]->(c:Context {source_type: $source_type})
            RETURN c
            ORDER BY c.importance DESC, c.created_at DESC
            LIMIT $limit
            """
            params = {"topic_id": topic_id, "source_type": source_type, "limit": limit}
        else:
            query = """
            MATCH (t:Topic {id: $topic_id})-[:HAS_CONTEXT]->(c:Context)
            RETURN c
            ORDER BY c.importance DESC, c.created_at DESC
            LIMIT $limit
            """
            params = {"topic_id": topic_id, "limit": limit}

        async with neo4j_client.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return [dict(r["c"]) for r in records]

    async def search_topics(
        self,
        query_text: str,
        department_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for topics by name or description."""
        if department_id:
            query = """
            MATCH (d:Department {id: $department_id})-[:HAS_SUBDEPARTMENT]->(sd)-[:HAS_TOPIC]->(t:Topic)
            WHERE toLower(t.title) CONTAINS toLower($query_text)
               OR toLower(coalesce(t.description, '')) CONTAINS toLower($query_text)
            RETURN t, sd.title as subdepartment
            LIMIT $limit
            """
            params = {"department_id": department_id, "query_text": query_text, "limit": limit}
        else:
            query = """
            MATCH (t:Topic)
            WHERE toLower(t.title) CONTAINS toLower($query_text)
               OR toLower(coalesce(t.description, '')) CONTAINS toLower($query_text)
            OPTIONAL MATCH (sd:SubDepartment)-[:HAS_TOPIC]->(t)
            RETURN t, sd.title as subdepartment
            LIMIT $limit
            """
            params = {"query_text": query_text, "limit": limit}

        async with neo4j_client.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return [
                {**dict(r["t"]), "subdepartment": r.get("subdepartment")}
                for r in records
            ]


# Singleton instance
hierarchy_manager = HierarchyManager()
