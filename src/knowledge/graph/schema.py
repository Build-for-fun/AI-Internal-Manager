"""Neo4j schema definitions for the knowledge graph.

The knowledge graph follows a hierarchical "textbook-style" structure:

Department
  └── SubDepartment
        └── Topic
              └── Context (individual pieces of knowledge)
                    └── Summary (weekly/monthly consolidations)

Additional node types:
- Entity: Named entities (projects, tools, concepts)
- Person: Team members
- Decision: Documented decisions
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class NodeLabels(str, Enum):
    """Node labels for the knowledge graph."""

    DEPARTMENT = "Department"
    SUB_DEPARTMENT = "SubDepartment"
    TOPIC = "Topic"
    CONTEXT = "Context"
    SUMMARY = "Summary"
    ENTITY = "Entity"
    PERSON = "Person"
    PROJECT = "Project"
    DECISION = "Decision"


class RelationshipTypes(str, Enum):
    """Relationship types for the knowledge graph."""

    # Hierarchical relationships
    HAS_SUBDEPARTMENT = "HAS_SUBDEPARTMENT"
    HAS_TOPIC = "HAS_TOPIC"
    HAS_CONTEXT = "HAS_CONTEXT"
    HAS_SUMMARY = "HAS_SUMMARY"

    # Entity relationships
    MENTIONS = "MENTIONS"
    REFERENCES = "REFERENCES"
    RELATES_TO = "RELATES_TO"
    PART_OF = "PART_OF"

    # Ownership and authorship
    OWNED_BY = "OWNED_BY"
    AUTHORED_BY = "AUTHORED_BY"
    DECIDED_BY = "DECIDED_BY"

    # Temporal relationships
    SUPERSEDES = "SUPERSEDES"
    PRECEDED_BY = "PRECEDED_BY"


@dataclass
class BaseNode:
    """Base class for all graph nodes."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]


@dataclass
class DepartmentNode(BaseNode):
    """Department node in the knowledge hierarchy."""

    description: str | None = None
    head_id: str | None = None  # Person node ID


@dataclass
class SubDepartmentNode(BaseNode):
    """Sub-department node."""

    department_id: str = ""
    description: str | None = None
    lead_id: str | None = None


@dataclass
class TopicNode(BaseNode):
    """Topic node representing a knowledge area."""

    sub_department_id: str = ""
    description: str | None = None
    importance: float = 0.5  # 0-1 scale
    last_updated_context: datetime | None = None


@dataclass
class ContextNode(BaseNode):
    """Context node representing individual knowledge pieces.

    This is the primary unit of knowledge, extracted from:
    - Jira issues
    - GitHub PRs and commits
    - Slack conversations
    - Documentation
    """

    topic_id: str = ""
    content: str = ""
    source_type: str = ""  # "jira", "github", "slack", "document"
    source_id: str = ""  # Original source identifier
    source_url: str | None = None
    embedding_id: str | None = None  # Reference to vector store
    importance: float = 0.5
    expires_at: datetime | None = None


@dataclass
class SummaryNode(BaseNode):
    """Summary node for consolidated knowledge.

    Created by periodic consolidation pipelines:
    - Weekly summaries aggregate context nodes
    - Monthly summaries aggregate weekly summaries
    """

    topic_id: str = ""
    summary_type: str = ""  # "weekly", "monthly", "quarterly"
    content: str = ""
    period_start: datetime | None = None
    period_end: datetime | None = None
    source_context_ids: list[str] | None = None
    embedding_id: str | None = None


@dataclass
class EntityNode(BaseNode):
    """Entity node for named entities (tools, concepts, etc.)."""

    entity_type: str = ""  # "tool", "concept", "service", "api"
    description: str | None = None
    aliases: list[str] | None = None


@dataclass
class PersonNode(BaseNode):
    """Person node for team members."""

    email: str = ""
    role: str | None = None
    department_id: str | None = None
    team: str | None = None
    jira_account_id: str | None = None
    github_username: str | None = None
    slack_user_id: str | None = None
    expertise_areas: list[str] | None = None


@dataclass
class ProjectNode(BaseNode):
    """Project node for tracking projects."""

    description: str | None = None
    status: str = "active"  # "active", "completed", "archived"
    jira_project_key: str | None = None
    github_repo: str | None = None
    department_id: str | None = None


@dataclass
class DecisionNode(BaseNode):
    """Decision node for documented decisions."""

    content: str = ""
    context: str | None = None
    decision_type: str = ""  # "technical", "process", "policy"
    status: str = "active"  # "active", "superseded", "deprecated"
    rationale: str | None = None
    alternatives_considered: list[str] | None = None
    source_url: str | None = None


# Schema creation queries
SCHEMA_CONSTRAINTS = [
    # Unique constraints
    "CREATE CONSTRAINT department_id IF NOT EXISTS FOR (d:Department) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT subdepartment_id IF NOT EXISTS FOR (s:SubDepartment) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT context_id IF NOT EXISTS FOR (c:Context) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT summary_id IF NOT EXISTS FOR (s:Summary) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE",
    # Person email unique
    "CREATE CONSTRAINT person_email IF NOT EXISTS FOR (p:Person) REQUIRE p.email IS UNIQUE",
]

SCHEMA_INDEXES = [
    # Full-text search indexes
    "CREATE FULLTEXT INDEX context_content IF NOT EXISTS FOR (c:Context) ON EACH [c.content, c.title]",
    "CREATE FULLTEXT INDEX summary_content IF NOT EXISTS FOR (s:Summary) ON EACH [s.content, s.title]",
    "CREATE FULLTEXT INDEX decision_content IF NOT EXISTS FOR (d:Decision) ON EACH [d.content, d.title, d.rationale]",
    # Property indexes for common queries
    "CREATE INDEX context_source IF NOT EXISTS FOR (c:Context) ON (c.source_type)",
    "CREATE INDEX context_topic IF NOT EXISTS FOR (c:Context) ON (c.topic_id)",
    "CREATE INDEX summary_type IF NOT EXISTS FOR (s:Summary) ON (s.summary_type)",
    "CREATE INDEX person_department IF NOT EXISTS FOR (p:Person) ON (p.department_id)",
    "CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status)",
]
