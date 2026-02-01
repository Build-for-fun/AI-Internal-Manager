"""Chat schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role enum."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationType(str, Enum):
    """Conversation type enum."""

    CHAT = "chat"
    ONBOARDING = "onboarding"
    VOICE = "voice"
    ANALYTICS = "analytics"


class ChatMessage(BaseModel):
    """Schema for a chat message."""

    role: MessageRole
    content: str


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    title: str | None = None
    conversation_type: ConversationType = ConversationType.CHAT
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: str
    title: str | None
    conversation_type: str
    metadata: dict[str, Any] = Field(validation_alias="conversation_metadata")
    last_agent: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: str
    conversation_id: str
    role: str
    content: str
    agent: str | None
    sources: list[dict[str, Any]] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """Schema for chat request."""

    message: str
    include_sources: bool = True
    stream: bool = False


class ChatResponse(BaseModel):
    """Schema for chat response."""

    message: MessageResponse
    sources: list[dict[str, Any]] | None = None
    agent_used: str | None = None


class StreamChunk(BaseModel):
    """Schema for streaming response chunk."""

    type: str  # "content", "source", "done", "error"
    content: str | None = None
    source: dict[str, Any] | None = None
    agent: str | None = None
    message_id: str | None = None


class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages."""

    type: str  # "message", "ping", "pong", "error"
    payload: dict[str, Any] = Field(default_factory=dict)
