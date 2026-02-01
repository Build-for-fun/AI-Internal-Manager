"""
Ownership Recommender - Produces contact recommendations.

Combines ownership analysis and ranking to produce actionable
recommendations like:
"For this task, contact XYZ (worked on tickets A, B and PRs C, D)"
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.rbac.models import UserContext, ResourceType, AccessLevel
from src.rbac.guards import rbac_guard
from src.security.audit import audit_logger
from src.ownership.analyzer import OwnershipAnalyzer, ownership_analyzer
from src.ownership.ranker import ExpertiseRanker, RankedCandidate

logger = structlog.get_logger()


@dataclass
class ContactRecommendation:
    """A recommendation for who to contact."""

    # Primary recommendation
    primary_contact: RankedCandidate | None = None
    primary_reason: str = ""

    # Alternative contacts
    alternatives: list[RankedCandidate] = field(default_factory=list)

    # Context
    query: str = ""
    scope_applied: dict[str, Any] = field(default_factory=dict)

    # Formatted output
    summary: str = ""
    detailed_explanation: str = ""

    # Access control
    results_filtered: bool = False
    filter_reason: str = ""

    def to_response(self) -> dict[str, Any]:
        """Convert to API response format."""
        response = {
            "summary": self.summary,
            "query": self.query,
        }

        if self.primary_contact:
            response["primary"] = {
                "user_id": self.primary_contact.user_id,
                "name": self.primary_contact.user_name,
                "email": self.primary_contact.user_email,
                "score": round(self.primary_contact.total_score, 1),
                "reason": self.primary_reason,
                "evidence": self.primary_contact.key_artifacts,
            }

        if self.alternatives:
            response["alternatives"] = [
                {
                    "user_id": c.user_id,
                    "name": c.user_name,
                    "score": round(c.total_score, 1),
                }
                for c in self.alternatives
            ]

        if self.results_filtered:
            response["note"] = (
                "Some results were filtered based on your access permissions."
            )

        return response


class OwnershipRecommender:
    """
    Produces ownership recommendations with RBAC enforcement.

    Workflow:
    1. Check user permissions for ownership lookup
    2. Analyze ownership across sources (within permitted scope)
    3. Rank candidates
    4. Filter results based on user's visibility
    5. Generate recommendation with evidence
    """

    def __init__(self):
        self.analyzer = ownership_analyzer
        self.ranker = ExpertiseRanker()

    async def recommend(
        self,
        query: str,
        context: UserContext,
        max_recommendations: int = 3,
    ) -> ContactRecommendation:
        """
        Get ownership recommendation for a query.

        Args:
            query: What the user is looking for (e.g., "auth service", "payment integration")
            context: User context for RBAC
            max_recommendations: Maximum number of recommendations

        Returns:
            ContactRecommendation with ranked contacts
        """
        recommendation = ContactRecommendation(query=query)

        # Check permission for ownership lookup
        decision = rbac_guard.check_access(
            context=context,
            resource=ResourceType.OWNERSHIP_LOOKUP,
            required_level=AccessLevel.READ,
        )

        if not decision.allowed:
            recommendation.results_filtered = True
            recommendation.filter_reason = decision.reason
            recommendation.summary = (
                "You don't have permission to look up ownership information."
            )
            return recommendation

        # Get scope filters from RBAC
        scope = decision.scope_filters
        recommendation.scope_applied = scope

        # Analyze ownership
        ownership_data = await self.analyzer.analyze_topic(
            topic=query,
            context=context,
            scope=scope,
        )

        # Rank candidates
        candidates = self.ranker.rank_candidates(
            ownership_data=ownership_data,
            max_candidates=max_recommendations + 2,  # Get extras for filtering
        )

        # Filter candidates based on user's visibility
        visible_candidates = await self._filter_visible_candidates(
            candidates, context, scope
        )

        if not visible_candidates:
            recommendation.summary = f"No experts found for '{query}' within your accessible scope."
            return recommendation

        # Mark if filtering occurred
        if len(visible_candidates) < len(candidates):
            recommendation.results_filtered = True
            recommendation.filter_reason = "Some experts were filtered based on your team/department access."

        # Build recommendation
        recommendation.primary_contact = visible_candidates[0]
        recommendation.primary_reason = self.ranker.explain_ranking(visible_candidates[0])
        recommendation.alternatives = visible_candidates[1:max_recommendations]

        # Generate summary
        recommendation.summary = self._generate_summary(
            query, visible_candidates[0], visible_candidates[1:max_recommendations]
        )
        recommendation.detailed_explanation = self._generate_detailed_explanation(
            visible_candidates[0]
        )

        # Audit the lookup
        audit_logger.log_ownership_lookup(
            context=context,
            query=query,
            results=[
                {"user_id": c.user_id, "score": c.total_score}
                for c in visible_candidates
            ],
            scope=scope,
        )

        logger.info(
            "Ownership recommendation generated",
            query=query,
            user_id=context.user_id,
            primary_contact=recommendation.primary_contact.user_id if recommendation.primary_contact else None,
            alternatives_count=len(recommendation.alternatives),
        )

        return recommendation

    async def _filter_visible_candidates(
        self,
        candidates: list[RankedCandidate],
        context: UserContext,
        scope: dict[str, Any],
    ) -> list[RankedCandidate]:
        """Filter candidates based on user's visibility permissions."""
        visible = []

        for candidate in candidates:
            # Check if user can view this candidate's information
            can_view = rbac_guard.can_view_employee_data(
                context=context,
                target_user_id=candidate.user_id,
                target_team_id=candidate.team_id or scope.get("team_id", ""),
            )

            if can_view:
                visible.append(candidate)

        return visible

    def _generate_summary(
        self,
        query: str,
        primary: RankedCandidate,
        alternatives: list[RankedCandidate],
    ) -> str:
        """Generate a natural language summary."""
        # Build primary contact string
        name = primary.user_name or primary.user_id

        # Collect evidence snippets
        evidence_parts = []

        jira_artifacts = [a for a in primary.key_artifacts if "jira" in a["type"]]
        github_artifacts = [a for a in primary.key_artifacts if "github" in a["type"]]

        if jira_artifacts:
            ticket_ids = [a["id"] for a in jira_artifacts[:2]]
            evidence_parts.append(f"tickets {', '.join(ticket_ids)}")

        if github_artifacts:
            pr_ids = [a["id"] for a in github_artifacts[:2]]
            evidence_parts.append(f"PRs {', '.join(pr_ids)}")

        # Build summary
        if evidence_parts:
            evidence_str = " and ".join(evidence_parts)
            summary = f"For '{query}', contact **{name}** (worked on {evidence_str})"
        else:
            summary = f"For '{query}', contact **{name}**"

        # Add confidence indicator
        if primary.total_score >= 70:
            summary += " - High confidence"
        elif primary.total_score >= 40:
            summary += " - Medium confidence"

        # Add alternatives
        if alternatives:
            alt_names = [a.user_name or a.user_id for a in alternatives[:2]]
            summary += f"\n\nAlternatives: {', '.join(alt_names)}"

        return summary

    def _generate_detailed_explanation(self, candidate: RankedCandidate) -> str:
        """Generate detailed explanation of why this person was recommended."""
        lines = [
            f"**{candidate.user_name or candidate.user_id}** (Score: {candidate.total_score:.1f}/100)",
            "",
            "**Score Breakdown:**",
            f"- Relevance: {candidate.relevance_score:.1f}",
            f"- Recency: {candidate.recency_score:.1f}",
            f"- Authority: {candidate.authority_score:.1f}",
            f"- Volume: {candidate.volume_score:.1f}",
            "",
            "**Source Contributions:**",
        ]

        if candidate.jira_score > 0:
            lines.append(f"- Jira: {candidate.jira_score:.1f}")
        if candidate.github_score > 0:
            lines.append(f"- GitHub: {candidate.github_score:.1f}")
        if candidate.slack_score > 0:
            lines.append(f"- Slack: {candidate.slack_score:.1f}")

        if candidate.key_artifacts:
            lines.extend(["", "**Key Evidence:**"])
            for artifact in candidate.key_artifacts:
                if artifact.get("url"):
                    lines.append(
                        f"- [{artifact['id']}]({artifact['url']}): {artifact.get('title', '')[:50]}"
                    )
                else:
                    lines.append(
                        f"- {artifact['id']}: {artifact.get('title', '')[:50]}"
                    )

        return "\n".join(lines)

    async def find_experts_for_area(
        self,
        area: str,
        context: UserContext,
        min_expertise_score: float = 30.0,
    ) -> list[RankedCandidate]:
        """
        Find all experts for a given area.

        Useful for building expertise maps or finding backup contacts.
        """
        decision = rbac_guard.check_access(
            context=context,
            resource=ResourceType.EXPERTISE_SEARCH,
            required_level=AccessLevel.READ,
        )

        if not decision.allowed:
            return []

        ownership_data = await self.analyzer.analyze_topic(
            topic=area,
            context=context,
            scope=decision.scope_filters,
        )

        candidates = self.ranker.rank_candidates(
            ownership_data=ownership_data,
            max_candidates=20,
            min_score=min_expertise_score,
        )

        return await self._filter_visible_candidates(
            candidates, context, decision.scope_filters
        )


# Convenience function for agents
async def get_contact_recommendation(
    query: str,
    context: UserContext,
) -> str:
    """
    Get a formatted contact recommendation.

    For use by agents responding to "who should I contact" queries.
    """
    recommender = OwnershipRecommender()
    recommendation = await recommender.recommend(query=query, context=context)

    return recommendation.summary
