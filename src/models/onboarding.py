"""Onboarding models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User


class OnboardingStatus(str, Enum):
    """Onboarding status enum."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"


class TaskStatus(str, Enum):
    """Task status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class OnboardingProgress(Base, UUIDMixin, TimestampMixin):
    """Tracks overall onboarding progress for a user."""

    __tablename__ = "onboarding_progress"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Overall status
    status: Mapped[str] = mapped_column(
        String(50),
        default=OnboardingStatus.NOT_STARTED.value,
        nullable=False,
    )

    # Progress percentage (0-100)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)

    # Current phase (e.g., "company_overview", "team_intro", "tools_setup")
    current_phase: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Role-specific flow identifier
    onboarding_flow: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Knowledge assessment scores
    assessment_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Notes and feedback
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="onboarding_progress")
    tasks: Mapped[list["OnboardingTask"]] = relationship(
        "OnboardingTask",
        back_populates="onboarding_progress",
        cascade="all, delete-orphan",
        order_by="OnboardingTask.order",
    )

    def __repr__(self) -> str:
        return f"<OnboardingProgress {self.user_id} ({self.status})>"


class OnboardingTask(Base, UUIDMixin, TimestampMixin):
    """Individual onboarding task."""

    __tablename__ = "onboarding_tasks"

    onboarding_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("onboarding_progress.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Task details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase: Mapped[str] = mapped_column(String(100), nullable=False)

    # Ordering
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=TaskStatus.PENDING.value,
        nullable=False,
    )

    # Task type (e.g., "reading", "quiz", "interactive", "meeting")
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Content reference (e.g., knowledge graph node ID)
    content_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Completion details
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Required or optional
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    onboarding_progress: Mapped["OnboardingProgress"] = relationship(
        "OnboardingProgress",
        back_populates="tasks",
    )

    def __repr__(self) -> str:
        return f"<OnboardingTask {self.title} ({self.status})>"
