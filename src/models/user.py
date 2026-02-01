"""User model."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.conversation import Conversation
    from src.models.onboarding import OnboardingProgress


class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role and department
    role: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g., "Software Engineer"
    department: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g., "Engineering"
    team: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g., "Platform"

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # External integrations
    jira_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slack_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Preferences stored as JSON
    preferences: Mapped[dict[str, Any]] = mapped_column(
        Base.JSON_TYPE,
        default=dict,
        nullable=False,
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    onboarding_progress: Mapped["OnboardingProgress | None"] = relationship(
        "OnboardingProgress",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
