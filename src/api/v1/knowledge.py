"""Knowledge API endpoints."""

from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.knowledge.retrieval import hybrid_retriever
from src.knowledge.graph.client import neo4j_client
from src.knowledge.graph.schema import NodeLabels
from src.knowledge.textbook.hierarchy import hierarchy_manager
from src.models.database import get_db
from src.models.user import User
from src.rbac.guards import rbac_guard
from src.rbac.models import AccessLevel, ResourceType, Role, UserContext
from src.schemas.knowledge import (
    GraphNode,
    HierarchyResponse,
    NodeCreateRequest,
    NodeType,
    NodeUpdateRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

logger = structlog.get_logger()

router = APIRouter()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from auth token (dev placeholder)."""
    stmt = select(User).limit(1)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid4()),
            email="dev@example.com",
            hashed_password="dev",
            full_name="Development User",
            role="Software Engineer",
            department="Engineering",
            team="Platform",
        )
        db.add(user)
        await db.commit()

    return user


def build_user_context(user: User) -> UserContext:
    """Build RBAC context from user model."""
    return UserContext(
        user_id=user.id,
        role=Role.from_string(user.role or "ic"),
        team_id=user.team or "",
        department_id=user.department or "",
        organization_id="default",
        email=user.email,
        name=user.full_name,
    )


def enforce_knowledge_access(
    *,
    context: UserContext,
    level: AccessLevel,
    department_id: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Enforce knowledge access and return scope filters + effective department."""
    resources = [
        ResourceType.KNOWLEDGE_GLOBAL,
        ResourceType.KNOWLEDGE_DEPARTMENT,
        ResourceType.KNOWLEDGE_TEAM,
        ResourceType.KNOWLEDGE_PERSONAL,
    ]

    for resource in resources:
        decision = rbac_guard.check_access(
            context=context,
            resource=resource,
            required_level=level,
            resource_attrs={
                "owner_id": context.user_id,
                "team_id": context.team_id,
                "department_id": context.department_id,
            },
        )
        if not decision.allowed:
            continue

        scope_filters = decision.scope_filters or {}
        scoped_department = scope_filters.get("department_id")
        if scoped_department:
            if department_id and department_id != scoped_department:
                raise HTTPException(status_code=403, detail="Department access denied")
            return scope_filters, scoped_department

        return scope_filters, department_id

    raise HTTPException(status_code=403, detail="Knowledge access denied")


def matches_scope(item: dict[str, Any], scope_filters: dict[str, Any]) -> bool:
    """Check if an item matches RBAC scope filters."""
    if not scope_filters:
        return True

    def get_attr(key: str) -> Any:
        if key in item:
            return item.get(key)
        metadata = item.get("metadata") or {}
        if isinstance(metadata, dict) and key in metadata:
            return metadata.get(key)
        return None

    for key, value in scope_filters.items():
        if key == "max_depth":
            continue
        if get_attr(key) != value:
            return False

    return True


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    user: User = Depends(get_current_user),
) -> SearchResponse:
    """Semantic search across the knowledge base.

    Combines vector search, full-text search, and graph traversal.
    """
    import time

    start_time = time.time()

    context = build_user_context(user)
    scope_filters, scoped_department = enforce_knowledge_access(
        context=context,
        level=AccessLevel.READ,
        department_id=request.department,
    )

    # Perform hybrid search
    results = await hybrid_retriever.retrieve(
        query=request.query,
        top_k=request.limit,
        department=scoped_department,
        include_summaries=request.include_context,
    )

    # Enforce scope filters (team/personal)
    if scope_filters:
        results = [r for r in results if matches_scope(r, scope_filters)]

    # Filter by minimum score
    filtered_results = [r for r in results if r.get("score", 0) >= request.min_score]

    # Filter by node types if specified
    if request.node_types:
        type_values = [nt.value for nt in request.node_types]
        filtered_results = [
            r for r in filtered_results
            if r.get("node_type", "") in type_values
        ]

    # Get hierarchy paths for results
    search_results = []
    for r in filtered_results:
        node_id = r.get("id")
        path = None
        if node_id and request.include_context:
            try:
                path_nodes = await neo4j_client.get_path_to_root(node_id)
                path = [n.get("title", "") for n in path_nodes]
            except Exception:
                pass

        search_results.append(SearchResult(
            id=r.get("id", ""),
            node_type=r.get("node_type", "Unknown"),
            title=r.get("title", "Untitled"),
            content=r.get("text", r.get("content", ""))[:500],
            score=r.get("score", 0),
            metadata={
                "source": r.get("source"),
                "source_url": r.get("source_url"),
            },
            path=path,
        ))

    elapsed_ms = (time.time() - start_time) * 1000

    return SearchResponse(
        results=search_results,
        query=request.query,
        total=len(search_results),
        took_ms=elapsed_ms,
    )


@router.get("/graph/hierarchy", response_model=HierarchyResponse)
async def get_hierarchy(
    department_id: str | None = None,
    user: User = Depends(get_current_user),
) -> HierarchyResponse:
    """Get the textbook-style knowledge hierarchy."""
    context = build_user_context(user)
    scope_filters, scoped_department = enforce_knowledge_access(
        context=context,
        level=AccessLevel.READ,
        department_id=department_id,
    )
    hierarchy = await hierarchy_manager.get_hierarchy(scoped_department)

    # Convert to response format
    from src.schemas.knowledge import HierarchyNode

    def convert_to_hierarchy_node(node_data: dict, node_type: NodeType) -> HierarchyNode:
        children = []

        if "subdepartments" in node_data:
            for sd in node_data["subdepartments"]:
                children.append(convert_to_hierarchy_node(sd, NodeType.SUB_DEPARTMENT))
        elif "topics" in node_data:
            for t in node_data["topics"]:
                children.append(HierarchyNode(
                    id=t["id"],
                    node_type=NodeType.TOPIC,
                    title=t.get("title", ""),
                    children=[],
                    context_count=t.get("context_count", 0),
                ))

        return HierarchyNode(
            id=node_data["id"],
            node_type=node_type,
            title=node_data.get("title", ""),
            children=children,
            context_count=sum(c.context_count for c in children),
        )

    departments = [
        convert_to_hierarchy_node(d, NodeType.DEPARTMENT)
        for d in hierarchy.get("departments", [])
    ]

    max_depth = scope_filters.get("max_depth") if scope_filters else None
    if isinstance(max_depth, int) and max_depth > 0:
        def trim_depth(node, depth: int) -> None:
            if depth >= max_depth:
                node.children = []
                return
            for child in node.children:
                trim_depth(child, depth + 1)

        for dept in departments:
            trim_depth(dept, 1)

    return HierarchyResponse(
        departments=departments,
        total_nodes=hierarchy.get("total_nodes", 0),
    )


@router.get("/graph/node/{node_id}", response_model=GraphNode)
async def get_node(
    node_id: str,
    include_relationships: bool = False,
    user: User = Depends(get_current_user),
) -> GraphNode:
    """Get a specific node from the knowledge graph."""
    context = build_user_context(user)
    scope_filters, _ = enforce_knowledge_access(context=context, level=AccessLevel.READ)
    node = await neo4j_client.get_node(node_id)

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Determine node type from labels
    node_type = NodeType.CONTEXT  # Default
    if "Department" in str(node.get("labels", [])):
        node_type = NodeType.DEPARTMENT
    elif "SubDepartment" in str(node.get("labels", [])):
        node_type = NodeType.SUB_DEPARTMENT
    elif "Topic" in str(node.get("labels", [])):
        node_type = NodeType.TOPIC
    elif "Summary" in str(node.get("labels", [])):
        node_type = NodeType.SUMMARY
    elif "Entity" in str(node.get("labels", [])):
        node_type = NodeType.ENTITY
    elif "Person" in str(node.get("labels", [])):
        node_type = NodeType.PERSON

    metadata = dict(node)
    # Remove standard fields from metadata
    for key in ["id", "title", "content", "created_at", "updated_at"]:
        metadata.pop(key, None)

    if not matches_scope({**node, "metadata": metadata}, scope_filters):
        raise HTTPException(status_code=403, detail="Node access denied")

    return GraphNode(
        id=node.get("id", ""),
        node_type=node_type,
        title=node.get("title", ""),
        content=node.get("content"),
        metadata=metadata,
        created_at=node.get("created_at"),
        updated_at=node.get("updated_at"),
    )


@router.post("/graph/node", response_model=GraphNode)
async def create_node(
    request: NodeCreateRequest,
    user: User = Depends(get_current_user),
) -> GraphNode:
    """Create a new node in the knowledge graph."""
    context = build_user_context(user)
    enforce_knowledge_access(context=context, level=AccessLevel.WRITE)
    # Map node type to label
    label_map = {
        NodeType.DEPARTMENT: NodeLabels.DEPARTMENT,
        NodeType.SUB_DEPARTMENT: NodeLabels.SUB_DEPARTMENT,
        NodeType.TOPIC: NodeLabels.TOPIC,
        NodeType.CONTEXT: NodeLabels.CONTEXT,
        NodeType.SUMMARY: NodeLabels.SUMMARY,
        NodeType.ENTITY: NodeLabels.ENTITY,
        NodeType.PERSON: NodeLabels.PERSON,
        NodeType.PROJECT: NodeLabels.PROJECT,
        NodeType.DECISION: NodeLabels.DECISION,
    }

    label = label_map.get(request.node_type)
    if not label:
        raise HTTPException(status_code=400, detail="Invalid node type")

    properties = {
        "id": str(uuid4()),
        "title": request.title,
        "content": request.content,
        **request.metadata,
    }

    node = await neo4j_client.create_node(label, properties)

    # Create relationship to parent if provided
    if request.parent_id:
        # Determine relationship type based on node types
        rel_type_map = {
            NodeType.SUB_DEPARTMENT: "HAS_SUBDEPARTMENT",
            NodeType.TOPIC: "HAS_TOPIC",
            NodeType.CONTEXT: "HAS_CONTEXT",
            NodeType.SUMMARY: "HAS_SUMMARY",
        }
        rel_type = rel_type_map.get(request.node_type, "RELATES_TO")

        from src.knowledge.graph.schema import RelationshipTypes
        await neo4j_client.create_relationship(
            request.parent_id,
            node["id"],
            RelationshipTypes(rel_type),
        )

    return GraphNode(
        id=node.get("id", ""),
        node_type=request.node_type,
        title=node.get("title", ""),
        content=node.get("content"),
        metadata=request.metadata,
    )


@router.patch("/graph/node/{node_id}", response_model=GraphNode)
async def update_node(
    node_id: str,
    request: NodeUpdateRequest,
    user: User = Depends(get_current_user),
) -> GraphNode:
    """Update a node in the knowledge graph."""
    context = build_user_context(user)
    enforce_knowledge_access(context=context, level=AccessLevel.WRITE)
    # Get existing node
    existing = await neo4j_client.get_node(node_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Node not found")

    # Build update properties
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.content is not None:
        updates["content"] = request.content
    if request.metadata is not None:
        updates.update(request.metadata)

    if updates:
        node = await neo4j_client.update_node(node_id, updates)
    else:
        node = existing

    return GraphNode(
        id=node.get("id", ""),
        node_type=NodeType.CONTEXT,  # Would need to determine from labels
        title=node.get("title", ""),
        content=node.get("content"),
        metadata={},
    )


@router.delete("/graph/node/{node_id}")
async def delete_node(
    node_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a node from the knowledge graph."""
    context = build_user_context(user)
    enforce_knowledge_access(context=context, level=AccessLevel.WRITE)
    success = await neo4j_client.delete_node(node_id)

    if not success:
        raise HTTPException(status_code=404, detail="Node not found")

    return {"status": "deleted"}


@router.get("/graph/node/{node_id}/children")
async def get_children(
    node_id: str,
    child_type: NodeType | None = None,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get children of a node in the hierarchy."""
    context = build_user_context(user)
    scope_filters, _ = enforce_knowledge_access(context=context, level=AccessLevel.READ)
    label = None
    if child_type:
        label_map = {
            NodeType.SUB_DEPARTMENT: NodeLabels.SUB_DEPARTMENT,
            NodeType.TOPIC: NodeLabels.TOPIC,
            NodeType.CONTEXT: NodeLabels.CONTEXT,
        }
        label = label_map.get(child_type)

    children = await neo4j_client.get_children(node_id, label)

    filtered_children = []
    for c in children:
        child = c.get("child", {})
        child_payload = {
            "id": child.get("id"),
            "title": child.get("title"),
            "labels": c.get("labels", []),
            "metadata": child,
        }
        if matches_scope(child_payload, scope_filters):
            filtered_children.append(
                {
                    "id": child.get("id"),
                    "title": child.get("title"),
                    "labels": c.get("labels", []),
                }
            )

    return filtered_children


@router.get("/topics")
async def search_topics(
    q: str = Query(..., min_length=1),
    department_id: str | None = None,
    limit: int = 10,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Search for topics by name."""
    context = build_user_context(user)
    scope_filters, scoped_department = enforce_knowledge_access(
        context=context,
        level=AccessLevel.READ,
        department_id=department_id,
    )
    topics = await hierarchy_manager.search_topics(
        query_text=q,
        department_id=scoped_department,
        limit=limit,
    )

    return [t for t in topics if matches_scope(t, scope_filters)]


@router.get("/topics/{topic_id}/contexts")
async def get_topic_contexts(
    topic_id: str,
    source_type: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get context nodes for a topic."""
    context = build_user_context(user)
    scope_filters, _ = enforce_knowledge_access(context=context, level=AccessLevel.READ)
    contexts = await hierarchy_manager.get_contexts_for_topic(
        topic_id=topic_id,
        limit=limit,
        source_type=source_type,
    )

    return [c for c in contexts if matches_scope(c, scope_filters)]
