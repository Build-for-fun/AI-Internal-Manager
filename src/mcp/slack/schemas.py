"""Slack data schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class SlackUser(BaseModel):
    """Slack user schema."""

    id: str
    name: str
    real_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    is_bot: bool = False


class SlackChannel(BaseModel):
    """Slack channel schema."""

    id: str
    name: str
    is_private: bool = False
    is_archived: bool = False
    topic: str | None = None
    purpose: str | None = None
    member_count: int = 0
    created: datetime | None = None


class SlackMessage(BaseModel):
    """Slack message schema."""

    ts: str  # Timestamp (message ID)
    channel_id: str
    user: SlackUser | None = None
    text: str
    thread_ts: str | None = None  # Parent thread timestamp
    reply_count: int = 0
    reply_users_count: int = 0
    reactions: list[dict] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)
    blocks: list[dict] = Field(default_factory=list)
    created_at: datetime
    edited_at: datetime | None = None


class SlackTopicCluster(BaseModel):
    """Cluster of related messages around a topic."""

    topic: str
    summary: str
    message_count: int
    participants: list[SlackUser] = Field(default_factory=list)
    key_messages: list[SlackMessage] = Field(default_factory=list)
    start_time: datetime
    end_time: datetime
    channels: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class SlackDecisionTrail(BaseModel):
    """Documented decision trail from conversations."""

    decision: str
    context: str
    participants: list[SlackUser] = Field(default_factory=list)
    decision_maker: SlackUser | None = None
    channel: str
    thread_ts: str | None = None
    made_at: datetime
    supporting_messages: list[SlackMessage] = Field(default_factory=list)


class SlackChannelActivity(BaseModel):
    """Channel activity metrics."""

    channel: SlackChannel
    message_count: int = 0
    thread_count: int = 0
    active_users: int = 0
    avg_response_time_minutes: float = 0
    peak_hours: list[int] = Field(default_factory=list)
    top_contributors: list[SlackUser] = Field(default_factory=list)


class SlackCommunicationEdge(BaseModel):
    """Edge in communication graph between users."""

    from_user: SlackUser
    to_user: SlackUser
    message_count: int = 0
    reaction_count: int = 0
    thread_replies: int = 0
    channels_in_common: list[str] = Field(default_factory=list)


class SlackCommunicationGraph(BaseModel):
    """Communication graph for team analysis."""

    nodes: list[SlackUser] = Field(default_factory=list)
    edges: list[SlackCommunicationEdge] = Field(default_factory=list)
    clusters: list[list[str]] = Field(default_factory=list)  # User ID clusters
