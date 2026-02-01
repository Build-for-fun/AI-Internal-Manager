"""Jira data schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JiraUser(BaseModel):
    """Jira user schema."""

    account_id: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None


class JiraIssue(BaseModel):
    """Jira issue schema."""

    key: str
    id: str
    summary: str
    description: str | None = None
    issue_type: str
    status: str
    priority: str | None = None
    assignee: JiraUser | None = None
    reporter: JiraUser | None = None
    project_key: str
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    story_points: float | None = None
    sprint: str | None = None
    epic_key: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class JiraEpic(BaseModel):
    """Jira epic schema."""

    key: str
    id: str
    summary: str
    description: str | None = None
    status: str
    project_key: str
    total_story_points: float = 0
    completed_story_points: float = 0
    issue_count: int = 0
    completed_issue_count: int = 0
    start_date: datetime | None = None
    due_date: datetime | None = None


class JiraSprint(BaseModel):
    """Jira sprint schema."""

    id: int
    name: str
    state: str  # "active", "closed", "future"
    board_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    complete_date: datetime | None = None
    goal: str | None = None
    velocity: float | None = None
    committed_points: float = 0
    completed_points: float = 0


class JiraBlocker(BaseModel):
    """Jira blocker schema."""

    blocking_issue_key: str
    blocking_issue_summary: str
    blocked_issue_key: str
    blocked_issue_summary: str
    blocker_type: str  # "blocks", "is blocked by"
    created_at: datetime
    assignee: JiraUser | None = None
    days_blocked: int = 0


class JiraWorkloadItem(BaseModel):
    """Workload item for a team member."""

    user: JiraUser
    assigned_issues: int
    in_progress_issues: int
    total_story_points: float
    in_progress_story_points: float


class JiraVelocity(BaseModel):
    """Sprint velocity data."""

    sprint_name: str
    sprint_id: int
    committed_points: float
    completed_points: float
    completion_rate: float
    start_date: datetime | None = None
    end_date: datetime | None = None
