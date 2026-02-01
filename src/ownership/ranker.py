"""
Expertise Ranker - Ranks candidates by relevance, recency, and authority.

Combines signals from multiple sources to produce a ranked list of
experts for a given topic.
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.ownership.analyzer import OwnershipData, OwnershipSignal

logger = structlog.get_logger()


@dataclass
class RankedCandidate:
    """A ranked candidate with scoring breakdown."""

    user_id: str
    user_name: str | None = None
    user_email: str | None = None

    # Overall score (0-100)
    total_score: float = 0.0

    # Score components
    relevance_score: float = 0.0  # How relevant to the topic
    recency_score: float = 0.0  # How recent their work
    authority_score: float = 0.0  # Their authority level (code owner, epic lead)
    volume_score: float = 0.0  # Amount of related work

    # Source breakdown
    jira_score: float = 0.0
    github_score: float = 0.0
    slack_score: float = 0.0

    # Evidence
    key_artifacts: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    # Contact info
    team_id: str | None = None
    department_id: str | None = None

    def add_artifact(
        self,
        artifact_type: str,
        artifact_id: str,
        title: str | None = None,
        url: str | None = None,
    ) -> None:
        """Add a key artifact as evidence."""
        if len(self.key_artifacts) < 5:  # Keep top 5 artifacts
            self.key_artifacts.append(
                {
                    "type": artifact_type,
                    "id": artifact_id,
                    "title": title,
                    "url": url,
                }
            )


class ExpertiseRanker:
    """
    Ranks candidates based on ownership signals.

    Scoring factors:
    - Relevance: How closely their work matches the query
    - Recency: How recently they worked on related items
    - Authority: Whether they're code owners, epic leads, etc.
    - Volume: Total amount of related work
    """

    def __init__(self):
        # Weight factors for final score
        self._weights = {
            "relevance": 0.35,
            "recency": 0.25,
            "authority": 0.25,
            "volume": 0.15,
        }

        # Source weights
        self._source_weights = {
            "jira": 0.35,
            "github": 0.40,
            "slack": 0.25,
        }

        # Authority signal types
        self._authority_signals = {
            "jira_epic_owner",
            "github_code_owner",
            "github_approver",
            "slack_decision_maker",
        }

    def rank_candidates(
        self,
        ownership_data: OwnershipData,
        max_candidates: int = 10,
        min_score: float = 10.0,
    ) -> list[RankedCandidate]:
        """
        Rank candidates from ownership data.

        Args:
            ownership_data: Aggregated ownership signals
            max_candidates: Maximum number of candidates to return
            min_score: Minimum score threshold

        Returns:
            Sorted list of ranked candidates
        """
        # Group signals by user
        user_signals: dict[str, list[OwnershipSignal]] = {}
        for signal in ownership_data.signals:
            if signal.user_id not in user_signals:
                user_signals[signal.user_id] = []
            user_signals[signal.user_id].append(signal)

        # Score each user
        candidates = []
        for user_id, signals in user_signals.items():
            candidate = self._score_user(user_id, signals)
            if candidate.total_score >= min_score:
                candidates.append(candidate)

        # Sort by total score
        candidates.sort(key=lambda c: c.total_score, reverse=True)

        # Return top candidates
        return candidates[:max_candidates]

    def _score_user(
        self, user_id: str, signals: list[OwnershipSignal]
    ) -> RankedCandidate:
        """Calculate scores for a single user."""
        candidate = RankedCandidate(user_id=user_id, signal_count=len(signals))

        # Extract user info from signals
        for signal in signals:
            if signal.user_name and not candidate.user_name:
                candidate.user_name = signal.user_name
            if signal.user_email and not candidate.user_email:
                candidate.user_email = signal.user_email

        # Calculate component scores
        candidate.relevance_score = self._calculate_relevance(signals)
        candidate.recency_score = self._calculate_recency(signals)
        candidate.authority_score = self._calculate_authority(signals)
        candidate.volume_score = self._calculate_volume(signals)

        # Calculate source breakdown
        candidate.jira_score = self._calculate_source_score(signals, "jira")
        candidate.github_score = self._calculate_source_score(signals, "github")
        candidate.slack_score = self._calculate_source_score(signals, "slack")

        # Calculate total score (weighted combination, scaled to 0-100)
        raw_score = (
            self._weights["relevance"] * candidate.relevance_score
            + self._weights["recency"] * candidate.recency_score
            + self._weights["authority"] * candidate.authority_score
            + self._weights["volume"] * candidate.volume_score
        )

        # Source diversity bonus (up to 10%)
        source_count = sum(
            1
            for s in [
                candidate.jira_score,
                candidate.github_score,
                candidate.slack_score,
            ]
            if s > 0
        )
        diversity_bonus = (source_count - 1) * 0.05  # 5% per additional source

        candidate.total_score = min(100, raw_score * (1 + diversity_bonus))

        # Collect key artifacts
        self._collect_artifacts(candidate, signals)

        return candidate

    def _calculate_relevance(self, signals: list[OwnershipSignal]) -> float:
        """
        Calculate relevance score.

        Based on signal strength and type.
        """
        if not signals:
            return 0.0

        total_strength = sum(s.strength for s in signals)
        avg_strength = total_strength / len(signals)

        # Scale to 0-100
        return min(100, avg_strength * 50)

    def _calculate_recency(self, signals: list[OwnershipSignal]) -> float:
        """
        Calculate recency score.

        Based on how recent the signals are.
        """
        if not signals:
            return 0.0

        # Use max recency score (most recent signal)
        max_recency = max(s.recency_score for s in signals)

        # Also consider average
        avg_recency = sum(s.recency_score for s in signals) / len(signals)

        # Weighted combination (favor max)
        return (0.7 * max_recency + 0.3 * avg_recency) * 100

    def _calculate_authority(self, signals: list[OwnershipSignal]) -> float:
        """
        Calculate authority score.

        Based on whether user has authority signals (code owner, epic lead, etc.)
        """
        authority_signals = [
            s for s in signals if s.signal_type in self._authority_signals
        ]

        if not authority_signals:
            return 20.0  # Base authority for any contributor

        # Higher score for more/stronger authority signals
        authority_strength = sum(s.strength for s in authority_signals)

        return min(100, 20 + authority_strength * 30)

    def _calculate_volume(self, signals: list[OwnershipSignal]) -> float:
        """
        Calculate volume score.

        Based on total amount of related work.
        """
        # Scale based on signal count
        # 1 signal = ~20, 5+ signals = ~80+
        base_score = min(80, len(signals) * 15)

        # Bonus for diverse signal types
        signal_types = set(s.signal_type for s in signals)
        type_bonus = len(signal_types) * 5

        return min(100, base_score + type_bonus)

    def _calculate_source_score(
        self, signals: list[OwnershipSignal], source: str
    ) -> float:
        """Calculate score contribution from a specific source."""
        source_signals = [s for s in signals if s.source == source]

        if not source_signals:
            return 0.0

        total_strength = sum(s.strength * s.recency_score for s in source_signals)

        # Normalize to 0-100
        return min(100, total_strength * 20)

    def _collect_artifacts(
        self, candidate: RankedCandidate, signals: list[OwnershipSignal]
    ) -> None:
        """Collect top artifacts as evidence."""
        # Sort by strength * recency
        sorted_signals = sorted(
            [s for s in signals if s.artifact_id],
            key=lambda s: s.strength * s.recency_score,
            reverse=True,
        )

        for signal in sorted_signals[:5]:
            candidate.add_artifact(
                artifact_type=signal.signal_type,
                artifact_id=signal.artifact_id or "",
                title=signal.artifact_title,
                url=signal.artifact_url,
            )

    def explain_ranking(self, candidate: RankedCandidate) -> str:
        """Generate human-readable explanation of ranking."""
        explanations = []

        if candidate.authority_score > 50:
            explanations.append("has ownership/leadership role")

        if candidate.recency_score > 70:
            explanations.append("recently active in this area")
        elif candidate.recency_score > 40:
            explanations.append("has worked on this area")

        if candidate.volume_score > 60:
            explanations.append("significant contributor")

        # Source-specific explanations
        if candidate.github_score > 50:
            explanations.append("code contributions")
        if candidate.jira_score > 50:
            explanations.append("ticket ownership")
        if candidate.slack_score > 50:
            explanations.append("discussion participation")

        if explanations:
            return f"{candidate.user_name or candidate.user_id} ({', '.join(explanations)})"
        return candidate.user_name or candidate.user_id
