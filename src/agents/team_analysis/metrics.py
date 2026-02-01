"""Team health and performance metrics."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class HealthLevel(str, Enum):
    """Team health levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class MetricCategory(str, Enum):
    """Metric categories."""

    VELOCITY = "velocity"
    QUALITY = "quality"
    COLLABORATION = "collaboration"
    WORKLOAD = "workload"
    COMMUNICATION = "communication"


@dataclass
class TeamMetric:
    """A single team metric."""

    name: str
    value: float
    unit: str
    category: MetricCategory
    trend: str  # "up", "down", "stable"
    benchmark: float | None = None
    health_level: HealthLevel = HealthLevel.HEALTHY


@dataclass
class TeamHealthReport:
    """Comprehensive team health report."""

    team_id: str
    team_name: str
    generated_at: datetime
    overall_health: HealthLevel
    overall_score: float  # 0-100
    metrics: list[TeamMetric]
    insights: list[str]
    recommendations: list[str]


class MetricsCalculator:
    """Calculates team health metrics from various data sources."""

    @staticmethod
    def calculate_velocity_health(
        current_velocity: float,
        average_velocity: float,
        completion_rate: float,
    ) -> tuple[float, HealthLevel, str]:
        """Calculate velocity health score.

        Returns:
            (score, health_level, trend)
        """
        # Calculate variance from average
        if average_velocity == 0:
            variance = 0
        else:
            variance = (current_velocity - average_velocity) / average_velocity

        # Determine trend
        if variance > 0.1:
            trend = "up"
        elif variance < -0.1:
            trend = "down"
        else:
            trend = "stable"

        # Calculate score (0-100)
        score = min(100, max(0, 50 + (variance * 100) + (completion_rate * 50)))

        # Determine health
        if completion_rate >= 0.8 and variance >= -0.1:
            health = HealthLevel.HEALTHY
        elif completion_rate >= 0.6 or variance >= -0.2:
            health = HealthLevel.WARNING
        else:
            health = HealthLevel.CRITICAL

        return score, health, trend

    @staticmethod
    def calculate_workload_health(
        workload_items: list[dict[str, Any]],
    ) -> tuple[float, HealthLevel, list[str]]:
        """Calculate workload distribution health.

        Returns:
            (score, health_level, issues)
        """
        if not workload_items:
            return 50, HealthLevel.WARNING, ["No workload data available"]

        issues = []

        # Calculate utilization statistics
        utilizations = [item.get("utilization_percentage", 0) for item in workload_items]
        avg_utilization = sum(utilizations) / len(utilizations)
        max_utilization = max(utilizations)
        min_utilization = min(utilizations)

        # Check for overload
        overloaded = [item for item in workload_items if item.get("utilization_percentage", 0) > 100]
        if overloaded:
            issues.append(f"{len(overloaded)} team member(s) appear overloaded")

        # Check for underutilization
        underutilized = [item for item in workload_items if item.get("utilization_percentage", 0) < 50]
        if len(underutilized) > len(workload_items) / 2:
            issues.append("More than half the team appears underutilized")

        # Check for imbalance
        if max_utilization > 0 and (max_utilization - min_utilization) / max_utilization > 0.5:
            issues.append("Significant workload imbalance detected")

        # Check for blocked items
        total_blocked = sum(item.get("blocked_count", 0) for item in workload_items)
        if total_blocked > 3:
            issues.append(f"{total_blocked} blocked items need attention")

        # Calculate score
        score = 100
        if overloaded:
            score -= len(overloaded) * 15
        if total_blocked > 0:
            score -= total_blocked * 5
        if (max_utilization - min_utilization) > 50:
            score -= 10

        score = max(0, min(100, score))

        # Determine health
        if score >= 75:
            health = HealthLevel.HEALTHY
        elif score >= 50:
            health = HealthLevel.WARNING
        else:
            health = HealthLevel.CRITICAL

        return score, health, issues

    @staticmethod
    def calculate_quality_health(
        pr_merge_time_hours: float,
        review_coverage: float,
        bug_rate: float,
    ) -> tuple[float, HealthLevel]:
        """Calculate code quality health.

        Returns:
            (score, health_level)
        """
        score = 100

        # PR merge time (ideal: < 24 hours)
        if pr_merge_time_hours > 48:
            score -= 20
        elif pr_merge_time_hours > 24:
            score -= 10

        # Review coverage (ideal: 100%)
        score -= (1 - review_coverage) * 30

        # Bug rate (ideal: 0)
        score -= bug_rate * 20

        score = max(0, min(100, score))

        if score >= 75:
            health = HealthLevel.HEALTHY
        elif score >= 50:
            health = HealthLevel.WARNING
        else:
            health = HealthLevel.CRITICAL

        return score, health

    @staticmethod
    def calculate_collaboration_health(
        communication_score: float,  # 0-100
        cross_team_interactions: int,
        knowledge_sharing_events: int,
    ) -> tuple[float, HealthLevel]:
        """Calculate collaboration health.

        Returns:
            (score, health_level)
        """
        score = communication_score * 0.5

        # Cross-team interactions (ideal: at least 5 per week)
        if cross_team_interactions >= 5:
            score += 25
        else:
            score += cross_team_interactions * 5

        # Knowledge sharing (ideal: at least 2 per week)
        if knowledge_sharing_events >= 2:
            score += 25
        else:
            score += knowledge_sharing_events * 12.5

        score = max(0, min(100, score))

        if score >= 70:
            health = HealthLevel.HEALTHY
        elif score >= 50:
            health = HealthLevel.WARNING
        else:
            health = HealthLevel.CRITICAL

        return score, health

    @staticmethod
    def generate_insights(
        velocity_score: float,
        workload_score: float,
        quality_score: float,
        collaboration_score: float,
        workload_issues: list[str],
    ) -> list[str]:
        """Generate insights based on metrics."""
        insights = []

        # Velocity insights
        if velocity_score < 50:
            insights.append("Team velocity has dropped significantly. Consider reviewing sprint planning.")
        elif velocity_score > 80:
            insights.append("Team is maintaining strong velocity. Current processes are working well.")

        # Workload insights
        insights.extend(workload_issues)

        # Quality insights
        if quality_score < 60:
            insights.append("Code quality metrics indicate room for improvement in review processes.")

        # Collaboration insights
        if collaboration_score < 50:
            insights.append("Team collaboration appears low. Consider more cross-functional activities.")

        return insights

    @staticmethod
    def generate_recommendations(
        health_report: "TeamHealthReport",
    ) -> list[str]:
        """Generate recommendations based on health report."""
        recommendations = []

        for metric in health_report.metrics:
            if metric.health_level == HealthLevel.CRITICAL:
                if metric.category == MetricCategory.VELOCITY:
                    recommendations.append(
                        "Conduct a sprint retrospective to identify velocity blockers"
                    )
                elif metric.category == MetricCategory.WORKLOAD:
                    recommendations.append(
                        "Review task assignments and consider load balancing"
                    )
                elif metric.category == MetricCategory.QUALITY:
                    recommendations.append(
                        "Implement stricter code review requirements"
                    )
                elif metric.category == MetricCategory.COLLABORATION:
                    recommendations.append(
                        "Schedule regular team syncs and pair programming sessions"
                    )

        if health_report.overall_health == HealthLevel.CRITICAL:
            recommendations.insert(0, "Consider scheduling an urgent team health check meeting")

        return recommendations[:5]  # Top 5 recommendations
