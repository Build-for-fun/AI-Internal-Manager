"""Chat API endpoints with WebSocket support."""

import asyncio
import json
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.orchestrator.agent import orchestrator_agent
from src.models.conversation import Conversation, Message
from src.models.database import get_db
from src.models.user import User
from src.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    StreamChunk,
)
from src.rbac.models import Role, UserContext, ResourceType, AccessLevel
from src.rbac.guards import rbac_guard
from src.observability.keywords_ai import log_keywords_ai_chat

logger = structlog.get_logger()

router = APIRouter()


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


def enforce_access(
    *,
    context: UserContext,
    resource: ResourceType,
    level: AccessLevel,
    resource_attrs: dict[str, Any] | None = None,
) -> None:
    """Enforce RBAC access with HTTP-friendly errors."""
    try:
        rbac_guard.require_access(
            context=context,
            resource=resource,
            required_level=level,
            resource_attrs=resource_attrs,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


# Dependency to get current user (simplified - would use JWT in production)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from auth token.

    This is a simplified version. In production, extract user from JWT.
    """
    # For development, return first user or create one
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


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    """Create a new conversation."""
    context = build_user_context(user)
    enforce_access(
        context=context,
        resource=ResourceType.CHAT,
        level=AccessLevel.WRITE,
        resource_attrs={"owner_id": user.id},
    )
    conversation = Conversation(
        id=str(uuid4()),
        user_id=user.id,
        title=request.title,
        conversation_type=request.conversation_type.value,
        conversation_metadata=request.metadata,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    logger.info(
        "Conversation created",
        conversation_id=conversation.id,
        user_id=user.id,
    )

    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    """List user's conversations."""
    context = build_user_context(user)
    enforce_access(
        context=context,
        resource=ResourceType.CHAT_HISTORY,
        level=AccessLevel.READ,
        resource_attrs={"owner_id": user.id},
    )
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .where(Conversation.deleted_at.is_(None))
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    """Get a specific conversation."""
    context = build_user_context(user)
    enforce_access(
        context=context,
        resource=ResourceType.CHAT_HISTORY,
        level=AccessLevel.READ,
        resource_attrs={"owner_id": user.id},
    )
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Message]:
    """Get messages in a conversation."""
    context = build_user_context(user)
    enforce_access(
        context=context,
        resource=ResourceType.CHAT_HISTORY,
        level=AccessLevel.READ,
        resource_attrs={"owner_id": user.id},
    )
    # Verify conversation belongs to user
    conv_stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    conv_result = await db.execute(conv_stmt)
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())
    messages.reverse()  # Return in chronological order
    return messages


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: str,
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Send a message and get a response (non-streaming)."""
    context = build_user_context(user)
    enforce_access(
        context=context,
        resource=ResourceType.CHAT,
        level=AccessLevel.WRITE,
        resource_attrs={"owner_id": user.id},
    )
    # Get conversation
    conv_stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get recent messages for context
    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    msg_result = await db.execute(msg_stmt)
    recent_messages = list(msg_result.scalars().all())
    recent_messages.reverse()

    # Format messages for agent
    formatted_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in recent_messages
    ]

    # Store user message
    user_message = Message(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    # Process with orchestrator
    result = await orchestrator_agent.process(
        query=request.message,
        context={
            "conversation_id": conversation_id,
            "user_id": user.id,
            "user_name": user.full_name,
            "user_role": user.role,
            "user_department": user.department,
            "user_team": user.team,
            "conversation_type": conversation.conversation_type,
            "messages": formatted_messages,
        },
    )

    log_messages = formatted_messages + [{"role": "user", "content": request.message}]
    asyncio.create_task(
        log_keywords_ai_chat(
            messages=log_messages,
            output={"role": "assistant", "content": result["response"]},
            customer_identifier=user.id,
            model=orchestrator_agent.model,
        )
    )

    # Store assistant message
    assistant_message = Message(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=result["response"],
        agent=result.get("agent"),
        sources=result.get("sources"),
    )
    db.add(assistant_message)

    # Update conversation
    conversation.last_agent = result.get("agent")

    await db.commit()
    await db.refresh(assistant_message)

    return ChatResponse(
        message=MessageResponse.model_validate(assistant_message),
        sources=result.get("sources"),
        agent_used=result.get("agent"),
    )


@router.websocket("/ws/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    logger.info("WebSocket connected", conversation_id=conversation_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if message_data.get("type") != "message":
                continue

            user_message = message_data.get("content", "")
            user_id = message_data.get("user_id", "")

            # Process message
            try:
                result = await orchestrator_agent.process(
                    query=user_message,
                    context={
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "messages": [],  # Would load from DB
                    },
                )

                asyncio.create_task(
                    log_keywords_ai_chat(
                        messages=[{"role": "user", "content": user_message}],
                        output={"role": "assistant", "content": result["response"]},
                        customer_identifier=user_id,
                        model=orchestrator_agent.model,
                    )
                )

                # Send response
                await websocket.send_json({
                    "type": "message",
                    "content": result["response"],
                    "agent": result.get("agent"),
                    "sources": result.get("sources"),
                })

            except Exception as e:
                logger.error("Processing error", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "content": "An error occurred processing your message.",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", conversation_id=conversation_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get a streaming response.

    Returns Server-Sent Events (SSE) stream.
    """
    from fastapi.responses import StreamingResponse

    # Verify conversation exists
    conv_stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def generate():
        """Generate SSE events."""
        # For now, just return the full response
        # In production, implement actual streaming from Claude
        result = await orchestrator_agent.process(
            query=request.message,
            context={
                "conversation_id": conversation_id,
                "user_id": user.id,
                "user_name": user.full_name,
                "user_role": user.role,
                "user_department": user.department,
                "messages": [],
            },
        )

        asyncio.create_task(
            log_keywords_ai_chat(
                messages=[{"role": "user", "content": request.message}],
                output={"role": "assistant", "content": result["response"]},
                customer_identifier=user.id,
                model=orchestrator_agent.model,
            )
        )

        # Simulate streaming by chunking the response
        response = result["response"]
        chunk_size = 50

        for i in range(0, len(response), chunk_size):
            chunk = StreamChunk(
                type="content",
                content=response[i:i + chunk_size],
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
            await asyncio.sleep(0.05)  # Small delay for effect

        # Send sources
        if result.get("sources"):
            for source in result["sources"]:
                chunk = StreamChunk(type="source", source=source)
                yield f"data: {chunk.model_dump_json()}\n\n"

        # Send done
        done_chunk = StreamChunk(
            type="done",
            agent=result.get("agent"),
        )
        yield f"data: {done_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a conversation."""
    from datetime import datetime

    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.deleted_at = datetime.utcnow()
    await db.commit()

    return {"status": "deleted"}
