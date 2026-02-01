"""Internal analytics connector for querying Neo4j seeded data.

This connector provides tools that query the Neo4j database for team metrics,
sprint data, and other analytics that have been seeded or synced from external sources.
"""

from typing import Any

import structlog

from src.knowledge.graph.client import neo4j_client
from src.mcp.base import BaseMCPConnector, MCPTool, MCPToolParameter

logger = structlog.get_logger()


class InternalAnalyticsConnector(BaseMCPConnector):
    """Connector for internal analytics from Neo4j.

    Provides tools to query:
    - Team metrics (velocity, completion rates)
    - Sprint data
    - Jira issues
    - GitHub PRs and commits
    - Slack messages and decisions
    """

    def __init__(self):
        super().__init__(name="internal_analytics")

    async def connect(self) -> None:
        """Connect to Neo4j."""
        if not neo4j_client._driver:
            await neo4j_client.connect()
        self._connected = True
        logger.info("Internal analytics connector connected to Neo4j")

    async def disconnect(self) -> None:
        """Disconnect is handled by neo4j_client globally."""
        self._connected = False

    async def health_check(self) -> bool:
        """Check Neo4j connection."""
        try:
            await neo4j_client.verify_connectivity()
            return True
        except Exception:
            return False

    async def _run_query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run a Cypher query and return results as list of dicts."""
        params = params or {}
        async with neo4j_client.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return records

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_tools(self) -> list[MCPTool]:
        """Get available analytics tools."""
        return [
            MCPTool(
                name="get_team_velocity",
                description="Get sprint velocity data for a team. Returns velocity, completed points, and committed points for recent sprints.",
                category="jira_analytics",
                parameters=[
                    MCPToolParameter(
                        name="team_name",
                        type="string",
                        description="Team name (e.g., 'Platform', 'Backend', 'ML Platform')",
                        required=False,
                    ),
                    MCPToolParameter(
                        name="num_sprints",
                        type="integer",
                        description="Number of recent sprints to return (default: 5)",
                        required=False,
                        default=5,
                    ),
                ],
                handler=self._get_team_velocity,
            ),
            MCPTool(
                name="get_sprint_issues",
                description="Get Jira issues for a sprint, including status, assignees, and story points.",
                category="jira_analytics",
                parameters=[
                    MCPToolParameter(
                        name="sprint_id",
                        type="string",
                        description="Sprint ID (e.g., 'sprint-42')",
                        required=False,
                    ),
                ],
                handler=self._get_sprint_issues,
            ),
            MCPTool(
                name="get_team_metrics",
                description="Get detailed team metrics including velocity, bugs fixed, PRs merged, code review time, and deployment frequency.",
                category="jira_analytics",
                parameters=[
                    MCPToolParameter(
                        name="team_name",
                        type="string",
                        description="Team name to get metrics for",
                        required=False,
                    ),
                ],
                handler=self._get_team_metrics,
            ),
            MCPTool(
                name="get_pull_requests",
                description="Get recent pull requests with their status, authors, and linked Jira issues.",
                category="github_analytics",
                parameters=[
                    MCPToolParameter(
                        name="repo",
                        type="string",
                        description="Repository name (optional)",
                        required=False,
                    ),
                    MCPToolParameter(
                        name="state",
                        type="string",
                        description="PR state: 'open', 'merged', or 'all' (default: 'all')",
                        required=False,
                        default="all",
                    ),
                ],
                handler=self._get_pull_requests,
            ),
            MCPTool(
                name="get_slack_discussions",
                description="Get recent Slack messages and discussions, including decisions made.",
                category="slack_analytics",
                parameters=[
                    MCPToolParameter(
                        name="channel",
                        type="string",
                        description="Channel name (optional)",
                        required=False,
                    ),
                ],
                handler=self._get_slack_discussions,
            ),
            MCPTool(
                name="list_teams",
                description="List all teams with their current metrics summary.",
                category="jira_analytics",
                parameters=[],
                handler=self._list_teams,
            ),
        ]

    async def _get_team_velocity(
        self,
        team_name: str | None = None,
        num_sprints: int = 5,
    ) -> dict[str, Any]:
        """Get team velocity from Neo4j."""
        if team_name:
            query = """
            MATCH (tm:TeamMetrics)
            WHERE toLower(tm.team) CONTAINS toLower($team_name)
            RETURN tm.team as team, tm.sprint as sprint, tm.velocity as velocity,
                   tm.completed_points as completed_points, tm.committed_points as committed_points
            ORDER BY tm.sprint DESC
            LIMIT $limit
            """
            params = {"team_name": team_name, "limit": num_sprints}
        else:
            query = """
            MATCH (tm:TeamMetrics)
            RETURN tm.team as team, tm.sprint as sprint, tm.velocity as velocity,
                   tm.completed_points as completed_points, tm.committed_points as committed_points
            ORDER BY tm.sprint DESC
            LIMIT $limit
            """
            params = {"limit": num_sprints}

        results = await self._run_query(query, params)

        if not results:
            return {"message": f"No velocity data found for team '{team_name}'", "data": []}

        return {
            "message": f"Found {len(results)} sprint velocity records",
            "data": results,
        }

    async def _get_sprint_issues(
        self,
        sprint_id: str | None = None,
    ) -> dict[str, Any]:
        """Get issues for a sprint."""
        if sprint_id:
            query = """
            MATCH (s:Sprint {id: $sprint_id})-[:CONTAINS_ISSUE]->(i:JiraIssue)
            OPTIONAL MATCH (p:Person)-[:ASSIGNED_TO]->(i)
            RETURN i.key as key, i.summary as summary, i.status as status,
                   i.priority as priority, i.story_points as story_points,
                   p.name as assignee
            """
            params = {"sprint_id": sprint_id}
        else:
            # Get issues from the most recent sprint
            query = """
            MATCH (s:Sprint)-[:CONTAINS_ISSUE]->(i:JiraIssue)
            WHERE s.state = 'active'
            OPTIONAL MATCH (p:Person)-[:ASSIGNED_TO]->(i)
            RETURN s.name as sprint, i.key as key, i.summary as summary,
                   i.status as status, i.priority as priority,
                   i.story_points as story_points, p.name as assignee
            """
            params = {}

        results = await self._run_query(query, params)

        if not results:
            return {"message": "No issues found", "data": []}

        return {
            "message": f"Found {len(results)} issues",
            "data": results,
        }

    async def _get_team_metrics(
        self,
        team_name: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed team metrics."""
        if team_name:
            query = """
            MATCH (tm:TeamMetrics)
            WHERE toLower(tm.team) CONTAINS toLower($team_name)
            RETURN tm.team as team, tm.sprint as sprint, tm.velocity as velocity,
                   tm.completed_points as completed_points, tm.committed_points as committed_points,
                   tm.bugs_fixed as bugs_fixed, tm.prs_merged as prs_merged,
                   tm.code_review_time_avg_hours as code_review_time_hours,
                   tm.deployment_frequency as deployment_frequency,
                   tm.incident_count as incident_count
            ORDER BY tm.sprint DESC
            """
            params = {"team_name": team_name}
        else:
            query = """
            MATCH (tm:TeamMetrics)
            RETURN tm.team as team, tm.sprint as sprint, tm.velocity as velocity,
                   tm.completed_points as completed_points, tm.committed_points as committed_points,
                   tm.bugs_fixed as bugs_fixed, tm.prs_merged as prs_merged,
                   tm.code_review_time_avg_hours as code_review_time_hours,
                   tm.deployment_frequency as deployment_frequency,
                   tm.incident_count as incident_count
            ORDER BY tm.team, tm.sprint DESC
            """
            params = {}

        results = await self._run_query(query, params)

        if not results:
            return {"message": "No metrics found", "data": []}

        return {
            "message": f"Found metrics for {len(results)} sprint(s)",
            "data": results,
        }

    async def _get_pull_requests(
        self,
        repo: str | None = None,
        state: str = "all",
    ) -> dict[str, Any]:
        """Get pull requests from Neo4j."""
        conditions = []
        params: dict[str, Any] = {}

        if repo:
            conditions.append("pr.repo = $repo")
            params["repo"] = repo
        if state != "all":
            conditions.append("pr.state = $state")
            params["state"] = state

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (pr:PullRequest)
        {where_clause}
        OPTIONAL MATCH (pr)-[:IMPLEMENTS]->(i:JiraIssue)
        RETURN pr.number as number, pr.title as title, pr.state as state,
               pr.author as author, pr.repo as repo, pr.additions as additions,
               pr.deletions as deletions, pr.jira_key as jira_key,
               i.summary as jira_summary
        ORDER BY pr.number DESC
        LIMIT 10
        """

        results = await self._run_query(query, params)

        if not results:
            return {"message": "No pull requests found", "data": []}

        return {
            "message": f"Found {len(results)} pull requests",
            "data": results,
        }

    async def _get_slack_discussions(
        self,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """Get Slack discussions and decisions."""
        if channel:
            query = """
            MATCH (c:SlackChannel)-[:CONTAINS_MESSAGE]->(m:SlackMessage)
            WHERE toLower(c.name) CONTAINS toLower($channel)
            RETURN c.name as channel, m.author as author, m.content as content,
                   m.timestamp as timestamp, m.is_incident as is_incident
            ORDER BY m.timestamp DESC
            LIMIT 20
            """
            params = {"channel": channel}
        else:
            query = """
            MATCH (c:SlackChannel)-[:CONTAINS_MESSAGE]->(m:SlackMessage)
            RETURN c.name as channel, m.author as author, m.content as content,
                   m.timestamp as timestamp, m.is_incident as is_incident
            ORDER BY m.timestamp DESC
            LIMIT 20
            """
            params = {}

        results = await self._run_query(query, params)

        # Also get decisions
        decision_query = """
        MATCH (d:Decision)
        RETURN d.title as title, d.content as content, d.status as status,
               d.decision_date as date, d.participants as participants
        ORDER BY d.decision_date DESC
        LIMIT 5
        """
        decisions = await self._run_query(decision_query, {})

        return {
            "message": f"Found {len(results)} messages and {len(decisions)} decisions",
            "messages": results,
            "decisions": decisions,
        }

    async def _list_teams(self) -> dict[str, Any]:
        """List all teams with metrics."""
        query = """
        MATCH (tm:TeamMetrics)
        WITH tm.team as team, collect({
            sprint: tm.sprint,
            velocity: tm.velocity,
            completed: tm.completed_points,
            committed: tm.committed_points
        }) as sprints
        RETURN team, sprints
        ORDER BY team
        """
        results = await self._run_query(query, {})

        if not results:
            return {"message": "No teams found", "teams": []}

        return {
            "message": f"Found {len(results)} teams",
            "teams": results,
        }


# Singleton instance
internal_analytics_connector = InternalAnalyticsConnector()
