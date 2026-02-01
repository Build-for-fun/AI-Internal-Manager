"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.team_analysis.agent import team_analysis_agent
from src.models.database import get_db
from src.schemas.analytics import (
    Bottleneck,
    BottleneckAnalysisRequest,
    TeamAnalyticsResponse,
    TeamHealthScore,
    VelocityMetrics,
    WorkloadDistribution,
    WorkloadRequest,
)

logger = structlog.get_logger()

router = APIRouter()


@router.get("/team/{team_id}/health")
async def get_team_health(
    team_id: str,
    days: int = Query(default=14, ge=1, le=90),
) -> dict[str, Any]:
    """Get team health score and metrics."""
    try:
        report = await team_analysis_agent.get_team_health(team_id, days)

        return {
            "team_id": report.team_id,
            "team_name": report.team_name,
            "generated_at": report.generated_at.isoformat(),
            "overall_health": report.overall_health.value,
            "overall_score": report.overall_score,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "category": m.category.value,
                    "trend": m.trend,
                    "benchmark": m.benchmark,
                    "health_level": m.health_level.value,
                }
                for m in report.metrics
            ],
            "insights": report.insights,
            "recommendations": report.recommendations,
        }
    except Exception as e:
        logger.error("Failed to get team health", team_id=team_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to calculate team health")


@router.get("/team/{team_id}/velocity")
async def get_team_velocity(
    team_id: str,
    sprints: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """Get team velocity metrics across recent sprints."""
    from src.mcp.jira.connector import jira_connector

    try:
        # This would need actual board ID mapping
        velocity_data = await jira_connector.get_sprint_velocity(
            board_id=1,  # Would lookup from team_id
            num_sprints=sprints,
        )

        if not velocity_data:
            return {
                "team_id": team_id,
                "sprints": [],
                "average_velocity": 0,
                "trend": "unknown",
            }

        avg_velocity = sum(v.completed_points for v in velocity_data) / len(velocity_data)

        # Calculate trend
        if len(velocity_data) >= 2:
            recent = velocity_data[-1].completed_points
            previous = velocity_data[-2].completed_points
            if recent > previous * 1.1:
                trend = "up"
            elif recent < previous * 0.9:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        return {
            "team_id": team_id,
            "sprints": [
                {
                    "name": v.sprint_name,
                    "id": v.sprint_id,
                    "committed_points": v.committed_points,
                    "completed_points": v.completed_points,
                    "completion_rate": v.completion_rate,
                    "start_date": v.start_date.isoformat() if v.start_date else None,
                    "end_date": v.end_date.isoformat() if v.end_date else None,
                }
                for v in velocity_data
            ],
            "average_velocity": avg_velocity,
            "trend": trend,
        }
    except Exception as e:
        logger.error("Failed to get velocity", team_id=team_id, error=str(e))
        return {
            "team_id": team_id,
            "sprints": [],
            "average_velocity": 0,
            "trend": "unknown",
            "error": str(e),
        }


@router.get("/team/{team_id}/bottlenecks")
async def get_team_bottlenecks(
    team_id: str,
) -> dict[str, Any]:
    """Get identified bottlenecks for a team."""
    try:
        bottlenecks = await team_analysis_agent.identify_bottlenecks(team_id)

        return {
            "team_id": team_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "bottlenecks": bottlenecks,
            "total_count": len(bottlenecks),
            "critical_count": sum(1 for b in bottlenecks if b.get("severity") == "high"),
        }
    except Exception as e:
        logger.error("Failed to get bottlenecks", team_id=team_id, error=str(e))
        return {
            "team_id": team_id,
            "bottlenecks": [],
            "error": str(e),
        }


@router.post("/team/{team_id}/bottlenecks/analyze")
async def analyze_bottlenecks(
    team_id: str,
    request: BottleneckAnalysisRequest,
) -> dict[str, Any]:
    """Run detailed bottleneck analysis."""
    bottlenecks = []

    # Analyze code review bottlenecks
    if request.include_code_review:
        from src.mcp.github.connector import github_connector

        try:
            review_stats = await github_connector.get_review_stats(
                repo=f"company/{team_id}",  # Would need mapping
                days=request.lookback_days,
            )

            # Find reviewers with high load
            for stat in review_stats:
                if stat.reviews_given > 20 and stat.avg_review_time_hours > 24:
                    bottlenecks.append({
                        "type": "code_review",
                        "title": f"Review bottleneck: {stat.user.login}",
                        "description": f"High review load ({stat.reviews_given} reviews) with slow turnaround ({stat.avg_review_time_hours:.1f}h avg)",
                        "severity": "medium",
                        "affected_items": [],
                        "suggested_actions": [
                            "Distribute review load more evenly",
                            "Consider adding more reviewers",
                        ],
                    })
        except Exception as e:
            logger.warning("Code review analysis failed", error=str(e))

    # Analyze dependency bottlenecks
    if request.include_dependencies:
        from src.mcp.jira.connector import jira_connector

        try:
            blockers = await jira_connector.get_blockers(team_id)

            for blocker in blockers:
                if blocker.days_blocked > 3:
                    bottlenecks.append({
                        "type": "dependency",
                        "title": f"Blocked: {blocker.blocked_issue_key}",
                        "description": f"Blocked by {blocker.blocking_issue_key} for {blocker.days_blocked} days",
                        "severity": "high" if blocker.days_blocked > 5 else "medium",
                        "affected_items": [blocker.blocked_issue_key],
                        "suggested_actions": [
                            f"Review and resolve {blocker.blocking_issue_key}",
                            "Consider re-prioritizing blocking work",
                        ],
                    })
        except Exception as e:
            logger.warning("Dependency analysis failed", error=str(e))

    # Analyze communication bottlenecks
    if request.include_communication:
        from src.mcp.slack.connector import slack_connector

        try:
            # Would analyze response times, silo patterns, etc.
            pass
        except Exception as e:
            logger.warning("Communication analysis failed", error=str(e))

    return {
        "team_id": team_id,
        "analyzed_at": datetime.utcnow().isoformat(),
        "lookback_days": request.lookback_days,
        "bottlenecks": bottlenecks,
        "analysis_coverage": {
            "code_review": request.include_code_review,
            "dependencies": request.include_dependencies,
            "communication": request.include_communication,
        },
    }


@router.get("/team/{team_id}/workload")
async def get_team_workload(
    team_id: str,
) -> dict[str, Any]:
    """Get workload distribution for team members."""
    from src.mcp.jira.connector import jira_connector

    try:
        workload_items = await jira_connector.get_team_workload(team_id)

        # Calculate team totals
        total_points = sum(w.total_story_points for w in workload_items)
        total_in_progress = sum(w.in_progress_story_points for w in workload_items)

        # Calculate utilization (assuming 20 points capacity per person)
        capacity_per_person = 20
        distributions = []

        for w in workload_items:
            utilization = (w.total_story_points / capacity_per_person) * 100

            distributions.append({
                "member_id": w.user.account_id,
                "member_name": w.user.display_name,
                "assigned_points": w.total_story_points,
                "completed_points": 0,  # Would need to track
                "in_progress_count": w.in_progress_issues,
                "blocked_count": 0,  # Would need blocker data
                "utilization_percentage": min(utilization, 150),  # Cap at 150%
            })

        # Sort by utilization
        distributions.sort(key=lambda x: x["utilization_percentage"], reverse=True)

        return {
            "team_id": team_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "team_totals": {
                "total_assigned_points": total_points,
                "total_in_progress_points": total_in_progress,
                "member_count": len(workload_items),
                "avg_points_per_member": total_points / len(workload_items) if workload_items else 0,
            },
            "distributions": distributions,
            "warnings": [
                f"{d['member_name']} appears overloaded ({d['utilization_percentage']:.0f}% utilization)"
                for d in distributions
                if d["utilization_percentage"] > 100
            ],
        }
    except Exception as e:
        logger.error("Failed to get workload", team_id=team_id, error=str(e))
        return {
            "team_id": team_id,
            "distributions": [],
            "error": str(e),
        }


@router.get("/team/{team_id}/communication")
async def get_team_communication(
    team_id: str,
    days: int = Query(default=30, ge=1, le=90),
) -> dict[str, Any]:
    """Get team communication patterns from Slack."""
    from src.mcp.slack.connector import slack_connector

    try:
        # Would need channel mapping for team
        channel_ids = [f"team-{team_id}"]  # Simplified

        graph = await slack_connector.get_communication_graph(
            channel_ids=channel_ids,
            days=days,
        )

        return {
            "team_id": team_id,
            "period_days": days,
            "participants": len(graph.nodes),
            "interaction_pairs": len(graph.edges),
            "top_communicators": [
                {"user": n.name, "id": n.id}
                for n in sorted(
                    graph.nodes,
                    key=lambda x: sum(
                        1 for e in graph.edges
                        if e.from_user.id == x.id or e.to_user.id == x.id
                    ),
                    reverse=True,
                )[:5]
            ],
            "isolated_members": [
                n.name for n in graph.nodes
                if not any(e.from_user.id == n.id or e.to_user.id == n.id for e in graph.edges)
            ],
        }
    except Exception as e:
        logger.error("Failed to get communication data", team_id=team_id, error=str(e))
        return {
            "team_id": team_id,
            "error": str(e),
        }


@router.get("/team/{team_id}/summary")
async def get_team_summary(
    team_id: str,
) -> dict[str, Any]:
    """Get a comprehensive team summary for dashboards."""
    # Aggregate multiple metrics
    health_data = {}
    velocity_data = {}
    bottleneck_data = {}

    try:
        report = await team_analysis_agent.get_team_health(team_id, 14)
        health_data = {
            "overall_score": report.overall_score,
            "health_level": report.overall_health.value,
            "top_insight": report.insights[0] if report.insights else None,
        }
    except Exception:
        health_data = {"error": "Unable to calculate"}

    try:
        bottlenecks = await team_analysis_agent.identify_bottlenecks(team_id)
        bottleneck_data = {
            "total_count": len(bottlenecks),
            "critical_count": sum(1 for b in bottlenecks if b.get("severity") == "high"),
        }
    except Exception:
        bottleneck_data = {"error": "Unable to analyze"}

    return {
        "team_id": team_id,
        "generated_at": datetime.utcnow().isoformat(),
        "health": health_data,
        "bottlenecks": bottleneck_data,
        "quick_actions": [
            "Review blocked items" if bottleneck_data.get("critical_count", 0) > 0 else None,
            "Check workload distribution",
            "Schedule team sync",
        ],
    }
