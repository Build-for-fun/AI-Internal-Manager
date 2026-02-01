"""Team analysis agent for health metrics and insights."""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.agents.team_analysis.metrics import (
    HealthLevel,
    MetricCategory,
    MetricsCalculator,
    TeamHealthReport,
    TeamMetric,
)
from src.config import settings
from src.mcp.registry import mcp_registry

logger = structlog.get_logger()


class TeamAnalysisAgent(BaseAgent):
    """Agent specialized in team health analysis.

    This agent:
    1. Gathers data from Jira, GitHub, and Slack
    2. Calculates team health metrics
    3. Identifies bottlenecks and silos
    4. Provides actionable insights
    """

    def __init__(self):
        super().__init__(
            name="team_analysis",
            description="Analyzes team health, performance, and collaboration patterns",
        )
        # Get analytics tools
        self._tools = mcp_registry.get_tools_for_agent("team_analysis")

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a team analysis query.

        Handles:
        - Team health questions
        - Velocity and workload queries
        - Bottleneck identification
        - Communication pattern analysis
        """
        user_team = context.get("user_team")
        memory_context = context.get("memory_context", {})

        # Get team analytics context
        analytics_context = await self._get_analytics_context(user_team)

        # Build system prompt
        system = f"""You are a team analytics expert for an internal company system.
Your role is to analyze team performance, identify issues, and provide actionable recommendations.

ANALYSIS CAPABILITIES:
1. Sprint velocity and completion rates
2. Workload distribution across team members
3. Code review and quality metrics
4. Communication patterns and collaboration
5. Bottleneck and blocker identification

CURRENT TEAM CONTEXT:
{self._format_analytics_context(analytics_context)}

AVAILABLE DATA SOURCES:
- Jira: Sprint data, issues, blockers, workload
- GitHub: PRs, reviews, code ownership, activity
- Slack: Communication patterns, decisions, discussions

GUIDELINES:
1. Provide data-driven insights
2. Be specific about numbers and trends
3. Suggest actionable improvements
4. Highlight both problems and successes
5. Consider team dynamics and sustainability
"""

        # Build messages
        messages = context.get("messages", [])
        messages.append({"role": "user", "content": query})

        # Run with tools for live data
        result = await self._run_with_tools(
            messages=messages,
            system=system,
            max_iterations=5,
        )

        # Extract any metrics mentioned
        sources = [
            {"type": "tool_result", "tool": tc.get("tool"), "summary": str(tc.get("result"))[:200]}
            for tc in result.get("tool_results", [])[:3]
        ]

        return {
            "response": result["response"],
            "sources": sources,
            "tool_calls": result.get("tool_calls", []),
            "metadata": {
                "team": user_team,
                "usage": result.get("usage", {}),
            },
        }

    async def _get_analytics_context(self, team_id: str | None) -> dict[str, Any]:
        """Get analytics context from memory."""
        if not team_id:
            return {}

        from src.memory.manager import memory_manager
        return await memory_manager.get_analytics_context(team_id)

    def _format_analytics_context(self, context: dict[str, Any]) -> str:
        """Format analytics context for prompt."""
        if not context:
            return "No cached analytics context available. Will fetch live data."

        parts = []

        if context.get("decisions"):
            decisions = context["decisions"][:3]
            parts.append("Recent Decisions:\n" + "\n".join(
                f"- {d.get('decision', '')[:100]}" for d in decisions
            ))

        if context.get("norms"):
            norms = context["norms"][:3]
            parts.append("Team Norms:\n" + "\n".join(
                f"- {n.get('text', '')[:100]}" for n in norms
            ))

        return "\n\n".join(parts) if parts else "No cached context."

    async def get_team_health(
        self,
        team_id: str,
        days: int = 14,
    ) -> TeamHealthReport:
        """Generate a comprehensive team health report.

        Combines data from multiple sources to calculate health metrics.
        """
        from src.mcp.github.connector import github_connector
        from src.mcp.jira.connector import jira_connector

        metrics = []
        insights = []

        # Get Jira velocity data
        try:
            velocity_data = await jira_connector.get_sprint_velocity(
                board_id=1,  # Would need actual board ID
                num_sprints=3,
            )
            if velocity_data:
                latest = velocity_data[-1]
                avg_velocity = sum(v.completed_points for v in velocity_data) / len(velocity_data)

                v_score, v_health, v_trend = MetricsCalculator.calculate_velocity_health(
                    current_velocity=latest.completed_points,
                    average_velocity=avg_velocity,
                    completion_rate=latest.completion_rate,
                )

                metrics.append(TeamMetric(
                    name="Sprint Velocity",
                    value=latest.completed_points,
                    unit="story points",
                    category=MetricCategory.VELOCITY,
                    trend=v_trend,
                    benchmark=avg_velocity,
                    health_level=v_health,
                ))
        except Exception as e:
            logger.warning("Failed to get velocity data", error=str(e))

        # Get workload distribution
        try:
            workload_data = await jira_connector.get_team_workload(
                project_key="TEAM",  # Would need actual project key
            )
            workload_items = [
                {
                    "member": w.user.display_name,
                    "utilization_percentage": (w.total_story_points / 20) * 100,  # Assuming 20 points capacity
                    "blocked_count": 0,
                }
                for w in workload_data
            ]

            w_score, w_health, w_issues = MetricsCalculator.calculate_workload_health(workload_items)

            metrics.append(TeamMetric(
                name="Workload Balance",
                value=w_score,
                unit="score",
                category=MetricCategory.WORKLOAD,
                trend="stable",
                health_level=w_health,
            ))
            insights.extend(w_issues)
        except Exception as e:
            logger.warning("Failed to get workload data", error=str(e))

        # Get review stats from GitHub
        try:
            review_stats = await github_connector.get_review_stats(
                repo="company/main-repo",  # Would need actual repo
                days=days,
            )
            if review_stats:
                avg_review_time = sum(r.avg_review_time_hours for r in review_stats) / len(review_stats)

                q_score, q_health = MetricsCalculator.calculate_quality_health(
                    pr_merge_time_hours=avg_review_time,
                    review_coverage=0.95,  # Would calculate from data
                    bug_rate=0.1,  # Would calculate from data
                )

                metrics.append(TeamMetric(
                    name="Code Quality",
                    value=q_score,
                    unit="score",
                    category=MetricCategory.QUALITY,
                    trend="stable",
                    health_level=q_health,
                ))
        except Exception as e:
            logger.warning("Failed to get review stats", error=str(e))

        # Calculate overall health
        if metrics:
            avg_score = sum(
                m.value for m in metrics if m.category in [
                    MetricCategory.VELOCITY,
                    MetricCategory.WORKLOAD,
                    MetricCategory.QUALITY,
                ]
            ) / len(metrics)
        else:
            avg_score = 50

        if avg_score >= 75:
            overall_health = HealthLevel.HEALTHY
        elif avg_score >= 50:
            overall_health = HealthLevel.WARNING
        else:
            overall_health = HealthLevel.CRITICAL

        # Generate insights
        all_insights = MetricsCalculator.generate_insights(
            velocity_score=next((m.value for m in metrics if m.category == MetricCategory.VELOCITY), 50),
            workload_score=next((m.value for m in metrics if m.category == MetricCategory.WORKLOAD), 50),
            quality_score=next((m.value for m in metrics if m.category == MetricCategory.QUALITY), 50),
            collaboration_score=50,  # Would calculate from Slack data
            workload_issues=insights,
        )

        report = TeamHealthReport(
            team_id=team_id,
            team_name=team_id,  # Would lookup actual name
            generated_at=datetime.utcnow(),
            overall_health=overall_health,
            overall_score=avg_score,
            metrics=metrics,
            insights=all_insights,
            recommendations=[],
        )

        # Generate recommendations
        report.recommendations = MetricsCalculator.generate_recommendations(report)

        return report

    async def identify_bottlenecks(
        self,
        team_id: str,
    ) -> list[dict[str, Any]]:
        """Identify current bottlenecks for the team."""
        from src.mcp.jira.connector import jira_connector

        bottlenecks = []

        # Get blockers from Jira
        try:
            blockers = await jira_connector.get_blockers(
                project_key=team_id,
            )

            for blocker in blockers:
                bottlenecks.append({
                    "type": "blocker",
                    "title": f"{blocker.blocking_issue_key} blocking {blocker.blocked_issue_key}",
                    "description": blocker.blocking_issue_summary,
                    "severity": "high" if blocker.days_blocked > 3 else "medium",
                    "days_active": blocker.days_blocked,
                    "suggested_action": "Review and resolve blocking issue",
                })
        except Exception as e:
            logger.warning("Failed to get blockers", error=str(e))

        return bottlenecks


# Singleton instance
team_analysis_agent = TeamAnalysisAgent()
