"""Knowledge graph schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Knowledge graph node types."""

    DEPARTMENT = "Department"
    SUB_DEPARTMENT = "SubDepartment"
    TOPIC = "Topic"
    CONTEXT = "Context"
    SUMMARY = "Summary"
    ENTITY = "Entity"
    PERSON = "Person"
    PROJECT = "Project"
    DECISION = "Decision"


class RelationshipType(str, Enum):
    """Knowledge graph relationship types."""

    HAS_SUBDEPARTMENT = "HAS_SUBDEPARTMENT"
    HAS_TOPIC = "HAS_TOPIC"
    HAS_CONTEXT = "HAS_CONTEXT"
    HAS_SUMMARY = "HAS_SUMMARY"
    MENTIONS = "MENTIONS"
    REFERENCES = "REFERENCES"
    RELATES_TO = "RELATES_TO"
    PART_OF = "PART_OF"
    OWNED_BY = "OWNED_BY"
    DECIDED_BY = "DECIDED_BY"


class SearchRequest(BaseModel):
    """Schema for semantic search request."""

    query: str
    limit: int = Field(default=10, ge=1, le=100)
    node_types: list[NodeType] | None = None
    department: str | None = None
    include_context: bool = True
    min_score: float = Field(default=0.5, ge=0, le=1)


class SearchResult(BaseModel):
    """Schema for a single search result."""

    id: str
    node_type: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any]
    path: list[str] | None = None  # Hierarchy path


class SearchResponse(BaseModel):
    """Schema for search response."""

    results: list[SearchResult]
    query: str
    total: int
    took_ms: float


class GraphNode(BaseModel):
    """Schema for a knowledge graph node."""

    id: str
    node_type: NodeType
    title: str
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GraphRelationship(BaseModel):
    """Schema for a knowledge graph relationship."""

    id: str
    type: RelationshipType
    source_id: str
    target_id: str
    properties: dict[str, Any] = Field(default_factory=dict)


class HierarchyNode(BaseModel):
    """Schema for a hierarchy node with children."""

    id: str
    node_type: NodeType
    title: str
    children: list["HierarchyNode"] = Field(default_factory=list)
    context_count: int = 0


class HierarchyResponse(BaseModel):
    """Schema for hierarchy response (textbook structure)."""

    departments: list[HierarchyNode]
    total_nodes: int


class NodeCreateRequest(BaseModel):
    """Schema for creating a new node."""

    node_type: NodeType
    title: str
    content: str | None = None
    parent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeUpdateRequest(BaseModel):
    """Schema for updating a node."""

    title: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None


# Update forward reference
HierarchyNode.model_rebuild()
