"""Knowledge API endpoints."""

from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.knowledge.retrieval import hybrid_retriever
from src.knowledge.graph.client import neo4j_client
from src.knowledge.graph.schema import NodeLabels
from src.knowledge.textbook.hierarchy import hierarchy_manager
from src.models.database import get_db
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


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
) -> SearchResponse:
    """Semantic search across the knowledge base.

    Combines vector search, full-text search, and graph traversal.
    """
    import time

    start_time = time.time()

    # Perform hybrid search
    results = await hybrid_retriever.retrieve(
        query=request.query,
        top_k=request.limit,
        department=request.department,
        include_summaries=request.include_context,
    )

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
) -> HierarchyResponse:
    """Get the textbook-style knowledge hierarchy."""
    hierarchy = await hierarchy_manager.get_hierarchy(department_id)

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

    return HierarchyResponse(
        departments=departments,
        total_nodes=hierarchy.get("total_nodes", 0),
    )


@router.get("/graph/node/{node_id}", response_model=GraphNode)
async def get_node(
    node_id: str,
    include_relationships: bool = False,
) -> GraphNode:
    """Get a specific node from the knowledge graph."""
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
) -> GraphNode:
    """Create a new node in the knowledge graph."""
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
) -> GraphNode:
    """Update a node in the knowledge graph."""
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
async def delete_node(node_id: str):
    """Delete a node from the knowledge graph."""
    success = await neo4j_client.delete_node(node_id)

    if not success:
        raise HTTPException(status_code=404, detail="Node not found")

    return {"status": "deleted"}


@router.get("/graph/node/{node_id}/children")
async def get_children(
    node_id: str,
    child_type: NodeType | None = None,
) -> list[dict[str, Any]]:
    """Get children of a node in the hierarchy."""
    label = None
    if child_type:
        label_map = {
            NodeType.SUB_DEPARTMENT: NodeLabels.SUB_DEPARTMENT,
            NodeType.TOPIC: NodeLabels.TOPIC,
            NodeType.CONTEXT: NodeLabels.CONTEXT,
        }
        label = label_map.get(child_type)

    children = await neo4j_client.get_children(node_id, label)

    return [
        {
            "id": c.get("child", {}).get("id"),
            "title": c.get("child", {}).get("title"),
            "labels": c.get("labels", []),
        }
        for c in children
    ]


@router.get("/topics")
async def search_topics(
    q: str = Query(..., min_length=1),
    department_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search for topics by name."""
    topics = await hierarchy_manager.search_topics(
        query_text=q,
        department_id=department_id,
        limit=limit,
    )

    return topics


@router.get("/topics/{topic_id}/contexts")
async def get_topic_contexts(
    topic_id: str,
    source_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get context nodes for a topic."""
    contexts = await hierarchy_manager.get_contexts_for_topic(
        topic_id=topic_id,
        limit=limit,
        source_type=source_type,
    )

    return contexts
