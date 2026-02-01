"""Conversation and Message models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User


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


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Conversation model for storing chat sessions."""

    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conversation_type: Mapped[str] = mapped_column(
        String(50),
        default=ConversationType.CHAT.value,
        nullable=False,
    )

    # Metadata for the conversation
    conversation_metadata: Mapped[dict[str, Any]] = mapped_column(
        Base.JSON_TYPE,
        default=dict,
        nullable=False,
    )

    # Last agent that handled this conversation
    last_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Conversation state for LangGraph
    state: Mapped[dict[str, Any]] = mapped_column(
        Base.JSON_TYPE,
        default=dict,
        nullable=False,
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id}>"


class Message(Base, UUIDMixin, TimestampMixin):
    """Message model for storing individual messages in a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Which agent generated this message
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Tool calls and results
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(Base.JSON_TYPE, nullable=True)
    tool_results: Mapped[list[dict[str, Any]] | None] = mapped_column(Base.JSON_TYPE, nullable=True)

    # Sources used for RAG responses
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(Base.JSON_TYPE, nullable=True)

    # Token usage
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)

    # Message metadata
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        Base.JSON_TYPE,
        default=dict,
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} ({self.role})>"
