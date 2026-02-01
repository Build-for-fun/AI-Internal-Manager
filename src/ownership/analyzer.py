"""
Ownership Analyzer - Analyzes data sources to determine ownership.

Processes:
- Jira: ticket ownership, assignees, epic owners
- GitHub: commit history, PR authors, code owners
- Slack: decision makers, frequent contributors
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import structlog

from src.rbac.models import UserContext

logger = structlog.get_logger()


@dataclass
class OwnershipSignal:
    """A single ownership signal from a data source."""

    source: str  # "jira", "github", "slack"
    user_id: str
    user_name: str | None = None
    user_email: str | None = None

    # Signal type and strength
    signal_type: str = ""  # "author", "reviewer", "assignee", "commenter", etc.
    strength: float = 1.0  # 0.0 to 1.0

    # Context
    artifact_id: str | None = None  # ticket ID, PR number, etc.
    artifact_title: str | None = None
    artifact_url: str | None = None

    # Temporal
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recency_score: float = 1.0  # Decays over time

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OwnershipData:
    """Aggregated ownership data for a topic/area."""

    topic: str
    signals: list[OwnershipSignal] = field(default_factory=list)

    # Aggregated scores by user
    user_scores: dict[str, float] = field(default_factory=dict)

    # Source breakdown
    jira_signals: list[OwnershipSignal] = field(default_factory=list)
    github_signals: list[OwnershipSignal] = field(default_factory=list)
    slack_signals: list[OwnershipSignal] = field(default_factory=list)

    def add_signal(self, signal: OwnershipSignal) -> None:
        """Add a signal and update scores."""
        self.signals.append(signal)

        # Categorize by source
        if signal.source == "jira":
            self.jira_signals.append(signal)
        elif signal.source == "github":
            self.github_signals.append(signal)
        elif signal.source == "slack":
            self.slack_signals.append(signal)

        # Update user score
        current_score = self.user_scores.get(signal.user_id, 0.0)
        self.user_scores[signal.user_id] = (
            current_score + signal.strength * signal.recency_score
        )


class OwnershipAnalyzer:
    """
    Analyzes ownership across multiple data sources.

    Coordinates with MCP connectors to gather ownership signals.
    """

    def __init__(self):
        self._jira_client = None
        self._github_client = None
        self._slack_client = None

        # Signal weights by type
        self._signal_weights = {
            # Jira signals
            "jira_assignee": 1.0,
            "jira_reporter": 0.5,
            "jira_epic_owner": 1.2,
            "jira_commenter": 0.3,
            "jira_watcher": 0.1,
            # GitHub signals
            "github_author": 1.0,
            "github_reviewer": 0.7,
            "github_approver": 0.8,
            "github_committer": 0.9,
            "github_code_owner": 1.5,
            # Slack signals
            "slack_decision_maker": 1.0,
            "slack_frequent_contributor": 0.6,
            "slack_channel_owner": 0.8,
            "slack_thread_starter": 0.4,
        }

        # Recency decay (half-life in days)
        self._recency_half_life = 90  # 90 days

    async def analyze_topic(
        self,
        topic: str,
        context: UserContext,
        scope: dict[str, Any] | None = None,
    ) -> OwnershipData:
        """
        Analyze ownership for a topic across all sources.

        Args:
            topic: Search topic/query
            context: User context for access control
            scope: Optional scope filters from RBAC

        Returns:
            OwnershipData with aggregated signals
        """
        ownership = OwnershipData(topic=topic)
        scope = scope or {}

        # Gather signals from each source (in parallel if possible)
        jira_signals = await self._analyze_jira(topic, context, scope)
        github_signals = await self._analyze_github(topic, context, scope)
        slack_signals = await self._analyze_slack(topic, context, scope)

        # Add all signals
        for signal in jira_signals + github_signals + slack_signals:
            ownership.add_signal(signal)

        logger.info(
            "Ownership analysis complete",
            topic=topic,
            total_signals=len(ownership.signals),
            unique_users=len(ownership.user_scores),
        )

        return ownership

    async def _analyze_jira(
        self,
        topic: str,
        context: UserContext,
        scope: dict[str, Any],
    ) -> list[OwnershipSignal]:
        """Analyze Jira for ownership signals."""
        signals = []

        try:
            # Search for relevant issues
            # In production, this would call the Jira MCP connector
            issues = await self._search_jira_issues(topic, scope)

            for issue in issues:
                # Assignee signal
                if issue.get("assignee"):
                    signals.append(
                        OwnershipSignal(
                            source="jira",
                            user_id=issue["assignee"]["id"],
                            user_name=issue["assignee"].get("name"),
                            user_email=issue["assignee"].get("email"),
                            signal_type="jira_assignee",
                            strength=self._signal_weights["jira_assignee"],
                            artifact_id=issue["key"],
                            artifact_title=issue.get("summary"),
                            artifact_url=issue.get("url"),
                            timestamp=self._parse_timestamp(issue.get("updated")),
                            recency_score=self._calculate_recency(
                                issue.get("updated")
                            ),
                            metadata={"issue_type": issue.get("type")},
                        )
                    )

                # Reporter signal
                if issue.get("reporter"):
                    signals.append(
                        OwnershipSignal(
                            source="jira",
                            user_id=issue["reporter"]["id"],
                            user_name=issue["reporter"].get("name"),
                            signal_type="jira_reporter",
                            strength=self._signal_weights["jira_reporter"],
                            artifact_id=issue["key"],
                            artifact_title=issue.get("summary"),
                            timestamp=self._parse_timestamp(issue.get("created")),
                            recency_score=self._calculate_recency(
                                issue.get("created")
                            ),
                        )
                    )

                # Epic owner (higher weight)
                if issue.get("type") == "Epic" and issue.get("assignee"):
                    signals.append(
                        OwnershipSignal(
                            source="jira",
                            user_id=issue["assignee"]["id"],
                            user_name=issue["assignee"].get("name"),
                            signal_type="jira_epic_owner",
                            strength=self._signal_weights["jira_epic_owner"],
                            artifact_id=issue["key"],
                            artifact_title=issue.get("summary"),
                            recency_score=self._calculate_recency(
                                issue.get("updated")
                            ),
                        )
                    )

        except Exception as e:
            logger.error("Jira analysis failed", error=str(e))

        return signals

    async def _analyze_github(
        self,
        topic: str,
        context: UserContext,
        scope: dict[str, Any],
    ) -> list[OwnershipSignal]:
        """Analyze GitHub for ownership signals."""
        signals = []

        try:
            # Search for relevant PRs and commits
            prs = await self._search_github_prs(topic, scope)
            commits = await self._search_github_commits(topic, scope)

            # PR signals
            for pr in prs:
                # Author signal
                if pr.get("author"):
                    signals.append(
                        OwnershipSignal(
                            source="github",
                            user_id=pr["author"]["login"],
                            user_name=pr["author"].get("name"),
                            signal_type="github_author",
                            strength=self._signal_weights["github_author"],
                            artifact_id=f"PR #{pr['number']}",
                            artifact_title=pr.get("title"),
                            artifact_url=pr.get("url"),
                            timestamp=self._parse_timestamp(pr.get("updated_at")),
                            recency_score=self._calculate_recency(
                                pr.get("updated_at")
                            ),
                            metadata={
                                "state": pr.get("state"),
                                "additions": pr.get("additions"),
                                "deletions": pr.get("deletions"),
                            },
                        )
                    )

                # Reviewer signals
                for reviewer in pr.get("reviewers", []):
                    signals.append(
                        OwnershipSignal(
                            source="github",
                            user_id=reviewer["login"],
                            user_name=reviewer.get("name"),
                            signal_type="github_reviewer",
                            strength=self._signal_weights["github_reviewer"],
                            artifact_id=f"PR #{pr['number']}",
                            artifact_title=pr.get("title"),
                            recency_score=self._calculate_recency(
                                pr.get("updated_at")
                            ),
                        )
                    )

            # Commit signals
            for commit in commits:
                if commit.get("author"):
                    signals.append(
                        OwnershipSignal(
                            source="github",
                            user_id=commit["author"]["login"],
                            user_name=commit["author"].get("name"),
                            user_email=commit["author"].get("email"),
                            signal_type="github_committer",
                            strength=self._signal_weights["github_committer"],
                            artifact_id=commit.get("sha", "")[:7],
                            artifact_title=commit.get("message", "")[:100],
                            artifact_url=commit.get("url"),
                            timestamp=self._parse_timestamp(
                                commit.get("committed_date")
                            ),
                            recency_score=self._calculate_recency(
                                commit.get("committed_date")
                            ),
                            metadata={"files_changed": commit.get("files_changed", [])},
                        )
                    )

            # Code owners
            code_owners = await self._get_code_owners(topic, scope)
            for owner in code_owners:
                signals.append(
                    OwnershipSignal(
                        source="github",
                        user_id=owner["login"],
                        user_name=owner.get("name"),
                        signal_type="github_code_owner",
                        strength=self._signal_weights["github_code_owner"],
                        metadata={"paths": owner.get("paths", [])},
                    )
                )

        except Exception as e:
            logger.error("GitHub analysis failed", error=str(e))

        return signals

    async def _analyze_slack(
        self,
        topic: str,
        context: UserContext,
        scope: dict[str, Any],
    ) -> list[OwnershipSignal]:
        """Analyze Slack for ownership signals."""
        signals = []

        try:
            # Search for relevant messages
            messages = await self._search_slack_messages(topic, scope)

            # Track user contribution counts
            contribution_counts: dict[str, int] = {}

            for message in messages:
                user_id = message.get("user")
                if not user_id:
                    continue

                contribution_counts[user_id] = contribution_counts.get(user_id, 0) + 1

                # Thread starter gets extra weight
                if message.get("is_thread_parent"):
                    signals.append(
                        OwnershipSignal(
                            source="slack",
                            user_id=user_id,
                            user_name=message.get("user_name"),
                            signal_type="slack_thread_starter",
                            strength=self._signal_weights["slack_thread_starter"],
                            artifact_id=message.get("ts"),
                            artifact_title=message.get("text", "")[:100],
                            timestamp=self._parse_timestamp(message.get("ts")),
                            recency_score=self._calculate_recency(message.get("ts")),
                        )
                    )

                # Check for decision markers
                if self._is_decision_message(message.get("text", "")):
                    signals.append(
                        OwnershipSignal(
                            source="slack",
                            user_id=user_id,
                            user_name=message.get("user_name"),
                            signal_type="slack_decision_maker",
                            strength=self._signal_weights["slack_decision_maker"],
                            artifact_id=message.get("ts"),
                            artifact_title=message.get("text", "")[:100],
                            recency_score=self._calculate_recency(message.get("ts")),
                        )
                    )

            # Add frequent contributor signals
            for user_id, count in contribution_counts.items():
                if count >= 3:  # Threshold for "frequent"
                    signals.append(
                        OwnershipSignal(
                            source="slack",
                            user_id=user_id,
                            signal_type="slack_frequent_contributor",
                            strength=self._signal_weights["slack_frequent_contributor"]
                            * min(count / 10, 1.0),  # Scale with count
                            metadata={"message_count": count},
                        )
                    )

        except Exception as e:
            logger.error("Slack analysis failed", error=str(e))

        return signals

    def _is_decision_message(self, text: str) -> bool:
        """Check if a message indicates a decision."""
        decision_markers = [
            "let's go with",
            "we decided",
            "decision:",
            "agreed:",
            "final decision",
            "we'll use",
            "approved",
            "let's proceed with",
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in decision_markers)

    def _calculate_recency(self, timestamp_str: str | None) -> float:
        """Calculate recency score (0-1) based on timestamp."""
        if not timestamp_str:
            return 0.5  # Default for unknown

        try:
            timestamp = self._parse_timestamp(timestamp_str)
            age_days = (datetime.utcnow() - timestamp).days

            # Exponential decay with half-life
            import math

            return math.exp(-math.log(2) * age_days / self._recency_half_life)
        except Exception:
            return 0.5

    def _parse_timestamp(self, ts: str | None) -> datetime:
        """Parse various timestamp formats."""
        if not ts:
            return datetime.utcnow()

        try:
            # Try ISO format
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass

        try:
            # Try Slack timestamp (Unix epoch)
            return datetime.fromtimestamp(float(ts.split(".")[0]))
        except (ValueError, IndexError):
            pass

        return datetime.utcnow()

    # Placeholder methods for MCP connector calls
    async def _search_jira_issues(
        self, topic: str, scope: dict
    ) -> list[dict[str, Any]]:
        """Search Jira issues. In production, calls Jira MCP connector."""
        # TODO: Implement actual Jira search via MCP
        return []

    async def _search_github_prs(self, topic: str, scope: dict) -> list[dict[str, Any]]:
        """Search GitHub PRs. In production, calls GitHub MCP connector."""
        # TODO: Implement actual GitHub search via MCP
        return []

    async def _search_github_commits(
        self, topic: str, scope: dict
    ) -> list[dict[str, Any]]:
        """Search GitHub commits. In production, calls GitHub MCP connector."""
        # TODO: Implement actual GitHub search via MCP
        return []

    async def _get_code_owners(self, topic: str, scope: dict) -> list[dict[str, Any]]:
        """Get code owners. In production, calls GitHub MCP connector."""
        # TODO: Implement actual code owners lookup via MCP
        return []

    async def _search_slack_messages(
        self, topic: str, scope: dict
    ) -> list[dict[str, Any]]:
        """Search Slack messages. In production, calls Slack MCP connector."""
        # TODO: Implement actual Slack search via MCP
        return []


# Global analyzer instance
ownership_analyzer = OwnershipAnalyzer()
