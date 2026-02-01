"""Onboarding schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class TaskType(str, Enum):
    """Onboarding task type enum."""

    READING = "reading"
    QUIZ = "quiz"
    INTERACTIVE = "interactive"
    MEETING = "meeting"
    VOICE_SESSION = "voice_session"


class OnboardingStartRequest(BaseModel):
    """Schema for starting onboarding."""

    flow: str | None = None  # Role-specific flow, auto-detected if not provided
    preferences: dict[str, Any] = Field(default_factory=dict)


class OnboardingTaskResponse(BaseModel):
    """Schema for onboarding task response."""

    id: str
    title: str
    description: str | None
    phase: str
    order: int
    status: TaskStatus
    task_type: TaskType
    is_required: bool
    content_ref: str | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class OnboardingProgressResponse(BaseModel):
    """Schema for onboarding progress response."""

    id: str
    status: OnboardingStatus
    progress_percentage: int
    current_phase: str | None
    onboarding_flow: str | None
    started_at: datetime | None
    completed_at: datetime | None
    assessment_scores: dict[str, Any]
    tasks: list[OnboardingTaskResponse]

    model_config = {"from_attributes": True}


class OnboardingTaskUpdate(BaseModel):
    """Schema for updating an onboarding task."""

    status: TaskStatus | None = None
    completion_data: dict[str, Any] | None = None


class VoiceSessionRequest(BaseModel):
    """Schema for starting a voice onboarding session."""

    topic: str | None = None  # Current topic to discuss
    resume: bool = True  # Resume from last position
    user_role: str | None = None  # User role for context

    model_config = {"extra": "ignore"}  # Ignore unknown fields


class VoiceSessionResponse(BaseModel):
    """Schema for voice session response."""

    session_id: str
    websocket_url: str
    current_topic: str | None
    estimated_duration_minutes: int


class QuizQuestion(BaseModel):
    """Schema for a quiz question."""

    id: str
    question: str
    options: list[str]
    topic: str


class QuizSubmission(BaseModel):
    """Schema for quiz submission."""

    question_id: str
    answer: int  # Index of selected option


class QuizResult(BaseModel):
    """Schema for quiz result."""

    question_id: str
    correct: bool
    correct_answer: int
    explanation: str | None
