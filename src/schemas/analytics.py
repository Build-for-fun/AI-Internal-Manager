"""Analytics schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Team health status enum."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class MetricTrend(str, Enum):
    """Metric trend direction."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class TeamMember(BaseModel):
    """Schema for team member info."""

    id: str
    name: str
    role: str
    avatar_url: str | None = None


class TeamHealthScore(BaseModel):
    """Schema for team health score."""

    overall_score: float = Field(ge=0, le=100)
    status: HealthStatus
    velocity_score: float = Field(ge=0, le=100)
    quality_score: float = Field(ge=0, le=100)
    collaboration_score: float = Field(ge=0, le=100)
    morale_score: float = Field(ge=0, le=100)


class VelocityMetrics(BaseModel):
    """Schema for velocity metrics."""

    current_velocity: float
    average_velocity: float
    trend: MetricTrend
    sprint_completion_rate: float
    story_points_completed: int
    story_points_committed: int


class WorkloadDistribution(BaseModel):
    """Schema for workload distribution."""

    member_id: str
    member_name: str
    assigned_points: int
    completed_points: int
    in_progress_count: int
    blocked_count: int
    utilization_percentage: float


class Bottleneck(BaseModel):
    """Schema for identified bottleneck."""

    id: str
    type: str  # "code_review", "dependency", "resource", "process"
    title: str
    description: str
    severity: str  # "low", "medium", "high"
    affected_items: list[str]
    suggested_actions: list[str]
    detected_at: datetime


class CommunicationPattern(BaseModel):
    """Schema for communication pattern analysis."""

    channel: str
    message_count: int
    active_participants: int
    response_time_avg_hours: float
    peak_hours: list[int]
    top_topics: list[str]


class TeamAnalyticsResponse(BaseModel):
    """Schema for full team analytics response."""

    team_id: str
    team_name: str
    period_start: datetime
    period_end: datetime
    health: TeamHealthScore
    velocity: VelocityMetrics
    workload: list[WorkloadDistribution]
    bottlenecks: list[Bottleneck]
    communication: list[CommunicationPattern]
    insights: list[str]


class BottleneckAnalysisRequest(BaseModel):
    """Schema for bottleneck analysis request."""

    team_id: str
    include_code_review: bool = True
    include_dependencies: bool = True
    include_communication: bool = True
    lookback_days: int = Field(default=14, ge=1, le=90)


class WorkloadRequest(BaseModel):
    """Schema for workload analysis request."""

    team_id: str
    include_individual: bool = True
    include_projections: bool = False
    sprint_id: str | None = None
