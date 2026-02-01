"""GitHub data schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user schema."""

    login: str
    id: int
    avatar_url: str | None = None
    name: str | None = None
    email: str | None = None


class GitHubCommit(BaseModel):
    """GitHub commit schema."""

    sha: str
    message: str
    author: GitHubUser | None = None
    committer: GitHubUser | None = None
    committed_at: datetime
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    url: str


class GitHubPullRequest(BaseModel):
    """GitHub pull request schema."""

    number: int
    title: str
    body: str | None = None
    state: str  # "open", "closed", "merged"
    author: GitHubUser
    assignees: list[GitHubUser] = Field(default_factory=list)
    reviewers: list[GitHubUser] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None = None
    closed_at: datetime | None = None
    commits: int = 0
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    review_comments: int = 0
    url: str
    base_branch: str
    head_branch: str


class GitHubReview(BaseModel):
    """GitHub pull request review schema."""

    id: int
    pr_number: int
    reviewer: GitHubUser
    state: str  # "APPROVED", "CHANGES_REQUESTED", "COMMENTED", "PENDING"
    body: str | None = None
    submitted_at: datetime
    comments_count: int = 0


class GitHubCodeOwnership(BaseModel):
    """Code ownership analysis result."""

    path: str
    owners: list[GitHubUser] = Field(default_factory=list)
    commit_count: int = 0
    last_modified: datetime | None = None
    primary_owner: GitHubUser | None = None
    ownership_percentage: float = 0


class GitHubActivityHeatmap(BaseModel):
    """Activity heatmap data."""

    user: GitHubUser
    day_of_week: int  # 0-6 (Monday-Sunday)
    hour: int  # 0-23
    commit_count: int = 0
    pr_count: int = 0
    review_count: int = 0


class GitHubReviewStats(BaseModel):
    """Review statistics for a user or team."""

    user: GitHubUser
    reviews_given: int = 0
    reviews_received: int = 0
    avg_review_time_hours: float = 0
    approval_rate: float = 0
    comments_per_review: float = 0


class GitHubRepoStats(BaseModel):
    """Repository statistics."""

    repo: str
    total_commits: int = 0
    total_prs: int = 0
    open_prs: int = 0
    merged_prs: int = 0
    avg_pr_merge_time_hours: float = 0
    contributors: int = 0
    top_contributors: list[GitHubUser] = Field(default_factory=list)
