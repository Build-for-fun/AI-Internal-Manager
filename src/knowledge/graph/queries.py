"""Cypher query templates for knowledge graph operations."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CypherQuery:
    """A Cypher query with its parameters."""

    query: str
    params: dict[str, Any]


class QueryTemplates:
    """Collection of Cypher query templates for common operations."""

    # ========== Department queries ==========

    @staticmethod
    def create_department(name: str, description: str | None = None, head_id: str | None = None) -> CypherQuery:
        """Create a new department."""
        return CypherQuery(
            query="""
            CREATE (d:Department {
                id: randomUUID(),
                title: $name,
                description: $description,
                head_id: $head_id,
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN d
            """,
            params={"name": name, "description": description, "head_id": head_id},
        )

    @staticmethod
    def get_all_departments() -> CypherQuery:
        """Get all departments with their subdepartment counts."""
        return CypherQuery(
            query="""
            MATCH (d:Department)
            OPTIONAL MATCH (d)-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment)
            RETURN d, count(sd) as subdepartment_count
            ORDER BY d.title
            """,
            params={},
        )

    # ========== Hierarchy queries ==========

    @staticmethod
    def get_full_hierarchy() -> CypherQuery:
        """Get the complete textbook hierarchy."""
        return CypherQuery(
            query="""
            MATCH (d:Department)
            OPTIONAL MATCH (d)-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment)
            OPTIONAL MATCH (sd)-[:HAS_TOPIC]->(t:Topic)
            OPTIONAL MATCH (t)-[:HAS_CONTEXT]->(c:Context)
            WITH d, sd, t, count(c) as context_count
            RETURN d as department,
                   collect(DISTINCT {
                       subdepartment: sd,
                       topics: collect(DISTINCT {topic: t, context_count: context_count})
                   }) as hierarchy
            ORDER BY d.title
            """,
            params={},
        )

    @staticmethod
    def get_hierarchy_for_department(department_id: str) -> CypherQuery:
        """Get hierarchy for a specific department."""
        return CypherQuery(
            query="""
            MATCH (d:Department {id: $department_id})
            OPTIONAL MATCH (d)-[:HAS_SUBDEPARTMENT]->(sd:SubDepartment)
            OPTIONAL MATCH (sd)-[:HAS_TOPIC]->(t:Topic)
            OPTIONAL MATCH (t)-[:HAS_CONTEXT]->(c:Context)
            WITH d, sd, t, count(c) as context_count
            RETURN d as department,
                   sd as subdepartment,
                   collect({topic: t, context_count: context_count}) as topics
            ORDER BY sd.title, t.title
            """,
            params={"department_id": department_id},
        )

    @staticmethod
    def add_subdepartment(department_id: str, name: str, description: str | None = None) -> CypherQuery:
        """Add a subdepartment to a department."""
        return CypherQuery(
            query="""
            MATCH (d:Department {id: $department_id})
            CREATE (sd:SubDepartment {
                id: randomUUID(),
                title: $name,
                description: $description,
                department_id: $department_id,
                created_at: datetime(),
                updated_at: datetime()
            })
            CREATE (d)-[:HAS_SUBDEPARTMENT]->(sd)
            RETURN sd
            """,
            params={"department_id": department_id, "name": name, "description": description},
        )

    @staticmethod
    def add_topic(subdepartment_id: str, name: str, description: str | None = None) -> CypherQuery:
        """Add a topic to a subdepartment."""
        return CypherQuery(
            query="""
            MATCH (sd:SubDepartment {id: $subdepartment_id})
            CREATE (t:Topic {
                id: randomUUID(),
                title: $name,
                description: $description,
                sub_department_id: $subdepartment_id,
                importance: 0.5,
                created_at: datetime(),
                updated_at: datetime()
            })
            CREATE (sd)-[:HAS_TOPIC]->(t)
            RETURN t
            """,
            params={"subdepartment_id": subdepartment_id, "name": name, "description": description},
        )

    # ========== Context queries ==========

    @staticmethod
    def add_context(
        topic_id: str,
        title: str,
        content: str,
        source_type: str,
        source_id: str,
        source_url: str | None = None,
        embedding_id: str | None = None,
        importance: float = 0.5,
    ) -> CypherQuery:
        """Add a context node to a topic."""
        return CypherQuery(
            query="""
            MATCH (t:Topic {id: $topic_id})
            CREATE (c:Context {
                id: randomUUID(),
                title: $title,
                content: $content,
                source_type: $source_type,
                source_id: $source_id,
                source_url: $source_url,
                embedding_id: $embedding_id,
                importance: $importance,
                topic_id: $topic_id,
                created_at: datetime(),
                updated_at: datetime()
            })
            CREATE (t)-[:HAS_CONTEXT]->(c)
            SET t.last_updated_context = datetime()
            RETURN c
            """,
            params={
                "topic_id": topic_id,
                "title": title,
                "content": content,
                "source_type": source_type,
                "source_id": source_id,
                "source_url": source_url,
                "embedding_id": embedding_id,
                "importance": importance,
            },
        )

    @staticmethod
    def get_contexts_for_topic(topic_id: str, limit: int = 50) -> CypherQuery:
        """Get all contexts for a topic."""
        return CypherQuery(
            query="""
            MATCH (t:Topic {id: $topic_id})-[:HAS_CONTEXT]->(c:Context)
            RETURN c
            ORDER BY c.importance DESC, c.created_at DESC
            LIMIT $limit
            """,
            params={"topic_id": topic_id, "limit": limit},
        )

    @staticmethod
    def get_contexts_by_source(source_type: str, limit: int = 50) -> CypherQuery:
        """Get contexts by source type."""
        return CypherQuery(
            query="""
            MATCH (c:Context {source_type: $source_type})
            RETURN c
            ORDER BY c.created_at DESC
            LIMIT $limit
            """,
            params={"source_type": source_type, "limit": limit},
        )

    # ========== Summary queries ==========

    @staticmethod
    def create_weekly_summary(
        topic_id: str,
        title: str,
        content: str,
        period_start: str,
        period_end: str,
        source_context_ids: list[str],
    ) -> CypherQuery:
        """Create a weekly summary for a topic."""
        return CypherQuery(
            query="""
            MATCH (t:Topic {id: $topic_id})
            CREATE (s:Summary {
                id: randomUUID(),
                title: $title,
                content: $content,
                summary_type: 'weekly',
                topic_id: $topic_id,
                period_start: datetime($period_start),
                period_end: datetime($period_end),
                source_context_ids: $source_context_ids,
                created_at: datetime(),
                updated_at: datetime()
            })
            CREATE (t)-[:HAS_SUMMARY]->(s)
            RETURN s
            """,
            params={
                "topic_id": topic_id,
                "title": title,
                "content": content,
                "period_start": period_start,
                "period_end": period_end,
                "source_context_ids": source_context_ids,
            },
        )

    @staticmethod
    def get_summaries_for_topic(topic_id: str, summary_type: str | None = None) -> CypherQuery:
        """Get summaries for a topic."""
        if summary_type:
            return CypherQuery(
                query="""
                MATCH (t:Topic {id: $topic_id})-[:HAS_SUMMARY]->(s:Summary {summary_type: $summary_type})
                RETURN s
                ORDER BY s.period_end DESC
                """,
                params={"topic_id": topic_id, "summary_type": summary_type},
            )
        return CypherQuery(
            query="""
            MATCH (t:Topic {id: $topic_id})-[:HAS_SUMMARY]->(s:Summary)
            RETURN s
            ORDER BY s.period_end DESC
            """,
            params={"topic_id": topic_id},
        )

    # ========== Entity queries ==========

    @staticmethod
    def create_entity(
        name: str,
        entity_type: str,
        description: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherQuery:
        """Create an entity node."""
        return CypherQuery(
            query="""
            CREATE (e:Entity {
                id: randomUUID(),
                title: $name,
                entity_type: $entity_type,
                description: $description,
                aliases: $aliases,
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN e
            """,
            params={
                "name": name,
                "entity_type": entity_type,
                "description": description,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def link_context_to_entity(context_id: str, entity_id: str) -> CypherQuery:
        """Link a context node to an entity."""
        return CypherQuery(
            query="""
            MATCH (c:Context {id: $context_id})
            MATCH (e:Entity {id: $entity_id})
            MERGE (c)-[:MENTIONS]->(e)
            RETURN c, e
            """,
            params={"context_id": context_id, "entity_id": entity_id},
        )

    @staticmethod
    def get_contexts_mentioning_entity(entity_id: str, limit: int = 20) -> CypherQuery:
        """Get contexts that mention an entity."""
        return CypherQuery(
            query="""
            MATCH (c:Context)-[:MENTIONS]->(e:Entity {id: $entity_id})
            RETURN c
            ORDER BY c.created_at DESC
            LIMIT $limit
            """,
            params={"entity_id": entity_id, "limit": limit},
        )

    # ========== Person queries ==========

    @staticmethod
    def create_person(
        name: str,
        email: str,
        role: str | None = None,
        department_id: str | None = None,
        team: str | None = None,
    ) -> CypherQuery:
        """Create a person node."""
        return CypherQuery(
            query="""
            CREATE (p:Person {
                id: randomUUID(),
                title: $name,
                email: $email,
                role: $role,
                department_id: $department_id,
                team: $team,
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN p
            """,
            params={
                "name": name,
                "email": email,
                "role": role,
                "department_id": department_id,
                "team": team,
            },
        )

    @staticmethod
    def get_person_by_email(email: str) -> CypherQuery:
        """Get a person by email."""
        return CypherQuery(
            query="MATCH (p:Person {email: $email}) RETURN p",
            params={"email": email},
        )

    @staticmethod
    def get_people_in_department(department_id: str) -> CypherQuery:
        """Get all people in a department."""
        return CypherQuery(
            query="""
            MATCH (p:Person {department_id: $department_id})
            RETURN p
            ORDER BY p.title
            """,
            params={"department_id": department_id},
        )

    # ========== Decision queries ==========

    @staticmethod
    def create_decision(
        title: str,
        content: str,
        decision_type: str,
        context: str | None = None,
        rationale: str | None = None,
        source_url: str | None = None,
    ) -> CypherQuery:
        """Create a decision node."""
        return CypherQuery(
            query="""
            CREATE (d:Decision {
                id: randomUUID(),
                title: $title,
                content: $content,
                decision_type: $decision_type,
                context: $context,
                rationale: $rationale,
                source_url: $source_url,
                status: 'active',
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN d
            """,
            params={
                "title": title,
                "content": content,
                "decision_type": decision_type,
                "context": context,
                "rationale": rationale,
                "source_url": source_url,
            },
        )

    @staticmethod
    def get_recent_decisions(limit: int = 20, decision_type: str | None = None) -> CypherQuery:
        """Get recent decisions."""
        if decision_type:
            return CypherQuery(
                query="""
                MATCH (d:Decision {decision_type: $decision_type, status: 'active'})
                RETURN d
                ORDER BY d.created_at DESC
                LIMIT $limit
                """,
                params={"decision_type": decision_type, "limit": limit},
            )
        return CypherQuery(
            query="""
            MATCH (d:Decision {status: 'active'})
            RETURN d
            ORDER BY d.created_at DESC
            LIMIT $limit
            """,
            params={"limit": limit},
        )

    # ========== Search queries ==========

    @staticmethod
    def search_by_keywords(keywords: list[str], node_types: list[str] | None = None) -> CypherQuery:
        """Search for nodes containing keywords."""
        labels = node_types if node_types else ["Context", "Summary", "Decision", "Entity"]
        label_str = ":".join(labels)

        return CypherQuery(
            query=f"""
            MATCH (n)
            WHERE any(label IN labels(n) WHERE label IN $labels)
            AND any(keyword IN $keywords WHERE
                toLower(n.title) CONTAINS toLower(keyword) OR
                toLower(coalesce(n.content, '')) CONTAINS toLower(keyword)
            )
            RETURN n, labels(n) as node_labels,
                   size([keyword IN $keywords WHERE
                       toLower(n.title) CONTAINS toLower(keyword) OR
                       toLower(coalesce(n.content, '')) CONTAINS toLower(keyword)
                   ]) as match_count
            ORDER BY match_count DESC
            LIMIT 20
            """,
            params={"keywords": keywords, "labels": labels},
        )

    @staticmethod
    def find_related_contexts(context_id: str, max_hops: int = 2) -> CypherQuery:
        """Find contexts related to a given context through shared entities."""
        return CypherQuery(
            query="""
            MATCH (source:Context {id: $context_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(related:Context)
            WHERE related.id <> $context_id
            RETURN related, e.title as shared_entity, count(e) as shared_count
            ORDER BY shared_count DESC
            LIMIT 10
            """,
            params={"context_id": context_id, "max_hops": max_hops},
        )
