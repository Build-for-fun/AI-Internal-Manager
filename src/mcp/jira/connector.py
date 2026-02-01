"""Jira MCP Connector implementation."""

from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from src.config import settings
from src.mcp.base import BaseMCPConnector, MCPToolParameter
from src.mcp.jira.schemas import (
    JiraBlocker,
    JiraEpic,
    JiraIssue,
    JiraSprint,
    JiraUser,
    JiraVelocity,
    JiraWorkloadItem,
)

logger = structlog.get_logger()


class JiraConnector(BaseMCPConnector):
    """MCP Connector for Jira.

    Provides tools for:
    - Issue retrieval and search
    - Sprint and velocity metrics
    - Blocker detection
    - Workload analysis
    """

    def __init__(self):
        super().__init__("jira")
        self._client: httpx.AsyncClient | None = None
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all Jira tools."""

        # Get Issue
        self._create_tool(
            name="jira_get_issue",
            description="Get details of a specific Jira issue by key",
            parameters=[
                MCPToolParameter(
                    name="issue_key",
                    type="string",
                    description="The Jira issue key (e.g., PROJ-123)",
                ),
            ],
            handler=self.get_issue,
            category="jira_read",
        )

        # Search Issues
        self._create_tool(
            name="jira_search_issues",
            description="Search for Jira issues using JQL",
            parameters=[
                MCPToolParameter(
                    name="jql",
                    type="string",
                    description="JQL query string",
                ),
                MCPToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results",
                    required=False,
                    default=50,
                ),
            ],
            handler=self.search_issues,
            category="jira_read",
        )

        # Get Sprint Velocity
        self._create_tool(
            name="jira_get_sprint_velocity",
            description="Get velocity metrics for recent sprints",
            parameters=[
                MCPToolParameter(
                    name="board_id",
                    type="integer",
                    description="The Jira board ID",
                ),
                MCPToolParameter(
                    name="num_sprints",
                    type="integer",
                    description="Number of sprints to analyze",
                    required=False,
                    default=5,
                ),
            ],
            handler=self.get_sprint_velocity,
            category="jira_analytics",
        )

        # Get Blockers
        self._create_tool(
            name="jira_get_blockers",
            description="Get current blockers for a project or team",
            parameters=[
                MCPToolParameter(
                    name="project_key",
                    type="string",
                    description="The Jira project key",
                ),
            ],
            handler=self.get_blockers,
            category="jira_analytics",
        )

        # Get Epic Progress
        self._create_tool(
            name="jira_get_epic_progress",
            description="Get progress details for an epic",
            parameters=[
                MCPToolParameter(
                    name="epic_key",
                    type="string",
                    description="The epic key",
                ),
            ],
            handler=self.get_epic_progress,
            category="jira_read",
        )

        # Get Team Workload
        self._create_tool(
            name="jira_get_team_workload",
            description="Get workload distribution for team members",
            parameters=[
                MCPToolParameter(
                    name="project_key",
                    type="string",
                    description="The Jira project key",
                ),
            ],
            handler=self.get_team_workload,
            category="jira_analytics",
        )

    async def connect(self) -> None:
        """Connect to Jira API."""
        if not settings.jira_base_url or not settings.jira_api_token.get_secret_value():
            logger.warning("Jira credentials not configured")
            return

        self._client = httpx.AsyncClient(
            base_url=settings.jira_base_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            auth=(settings.jira_email, settings.jira_api_token.get_secret_value()),
            timeout=30.0,
        )
        self._connected = True
        logger.info("Jira connector connected")

    async def disconnect(self) -> None:
        """Disconnect from Jira API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def health_check(self) -> bool:
        """Check Jira API health."""
        if not self._client:
            return False
        try:
            response = await self._client.get("/rest/api/3/myself")
            return response.status_code == 200
        except Exception:
            return False

    async def get_issue(self, issue_key: str) -> JiraIssue:
        """Get a Jira issue by key."""
        response = await self._client.get(
            f"/rest/api/3/issue/{issue_key}",
            params={"expand": "renderedFields,changelog"},
        )
        response.raise_for_status()
        data = response.json()
        return self._parse_issue(data)

    async def search_issues(self, jql: str, max_results: int = 50) -> list[JiraIssue]:
        """Search for issues using JQL."""
        response = await self._client.post(
            "/rest/api/3/search",
            json={
                "jql": jql,
                "maxResults": max_results,
                "fields": [
                    "summary", "description", "issuetype", "status", "priority",
                    "assignee", "reporter", "project", "labels", "components",
                    "customfield_10016",  # Story points (common field)
                    "sprint", "parent", "created", "updated", "resolutiondate",
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_issue(issue) for issue in data.get("issues", [])]

    async def get_sprint_velocity(
        self,
        board_id: int,
        num_sprints: int = 5,
    ) -> list[JiraVelocity]:
        """Get velocity for recent sprints."""
        # Get closed sprints
        response = await self._client.get(
            f"/rest/agile/1.0/board/{board_id}/sprint",
            params={"state": "closed", "maxResults": num_sprints},
        )
        response.raise_for_status()
        sprints_data = response.json().get("values", [])

        velocities = []
        for sprint in sprints_data[-num_sprints:]:
            # Get sprint report
            report_response = await self._client.get(
                f"/rest/greenhopper/1.0/rapid/charts/sprintreport",
                params={"rapidViewId": board_id, "sprintId": sprint["id"]},
            )

            if report_response.status_code == 200:
                report = report_response.json()
                contents = report.get("contents", {})

                committed = sum(
                    i.get("estimateStatistic", {}).get("statFieldValue", {}).get("value", 0)
                    for i in contents.get("completedIssues", [])
                ) + sum(
                    i.get("estimateStatistic", {}).get("statFieldValue", {}).get("value", 0)
                    for i in contents.get("issuesNotCompletedInCurrentSprint", [])
                )

                completed = sum(
                    i.get("estimateStatistic", {}).get("statFieldValue", {}).get("value", 0)
                    for i in contents.get("completedIssues", [])
                )

                velocities.append(JiraVelocity(
                    sprint_name=sprint["name"],
                    sprint_id=sprint["id"],
                    committed_points=committed,
                    completed_points=completed,
                    completion_rate=completed / committed if committed > 0 else 0,
                    start_date=datetime.fromisoformat(sprint["startDate"].replace("Z", "+00:00"))
                    if sprint.get("startDate") else None,
                    end_date=datetime.fromisoformat(sprint["endDate"].replace("Z", "+00:00"))
                    if sprint.get("endDate") else None,
                ))

        return velocities

    async def get_blockers(self, project_key: str) -> list[JiraBlocker]:
        """Get current blockers in a project."""
        # Search for issues with blockers link
        jql = f'project = {project_key} AND issueFunction in linkedIssuesOf("resolution = Unresolved", "blocks")'

        try:
            response = await self._client.post(
                "/rest/api/3/search",
                json={
                    "jql": f"project = {project_key} AND status != Done",
                    "maxResults": 100,
                    "fields": ["summary", "issuelinks", "assignee", "created"],
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            # Fallback if issueFunction is not available
            return []

        blockers = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            links = fields.get("issuelinks", [])

            for link in links:
                link_type = link.get("type", {}).get("name", "")
                if link_type == "Blocks":
                    # This issue blocks another
                    if "outwardIssue" in link:
                        blocked = link["outwardIssue"]
                        blockers.append(JiraBlocker(
                            blocking_issue_key=issue["key"],
                            blocking_issue_summary=fields.get("summary", ""),
                            blocked_issue_key=blocked["key"],
                            blocked_issue_summary=blocked["fields"]["summary"],
                            blocker_type="blocks",
                            created_at=datetime.fromisoformat(
                                fields.get("created", "").replace("Z", "+00:00")
                            ),
                            assignee=self._parse_user(fields.get("assignee")),
                            days_blocked=self._calculate_days_blocked(fields.get("created")),
                        ))

        return blockers

    async def get_epic_progress(self, epic_key: str) -> JiraEpic:
        """Get progress for an epic."""
        # Get epic details
        epic_response = await self._client.get(f"/rest/api/3/issue/{epic_key}")
        epic_response.raise_for_status()
        epic_data = epic_response.json()

        # Get issues in epic
        issues_response = await self._client.post(
            "/rest/api/3/search",
            json={
                "jql": f'"Epic Link" = {epic_key} OR parent = {epic_key}',
                "maxResults": 200,
                "fields": ["status", "customfield_10016"],  # Story points
            },
        )
        issues_response.raise_for_status()
        issues_data = issues_response.json()

        issues = issues_data.get("issues", [])
        total_points = 0
        completed_points = 0
        completed_count = 0

        for issue in issues:
            fields = issue.get("fields", {})
            points = fields.get("customfield_10016") or 0
            total_points += points

            status = fields.get("status", {}).get("statusCategory", {}).get("key", "")
            if status == "done":
                completed_points += points
                completed_count += 1

        epic_fields = epic_data.get("fields", {})
        return JiraEpic(
            key=epic_data["key"],
            id=epic_data["id"],
            summary=epic_fields.get("summary", ""),
            description=epic_fields.get("description"),
            status=epic_fields.get("status", {}).get("name", ""),
            project_key=epic_fields.get("project", {}).get("key", ""),
            total_story_points=total_points,
            completed_story_points=completed_points,
            issue_count=len(issues),
            completed_issue_count=completed_count,
        )

    async def get_team_workload(self, project_key: str) -> list[JiraWorkloadItem]:
        """Get workload distribution for team members."""
        # Get active issues grouped by assignee
        response = await self._client.post(
            "/rest/api/3/search",
            json={
                "jql": f"project = {project_key} AND status != Done AND assignee IS NOT EMPTY",
                "maxResults": 500,
                "fields": ["assignee", "status", "customfield_10016"],
            },
        )
        response.raise_for_status()
        data = response.json()

        workload_map: dict[str, JiraWorkloadItem] = {}

        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            assignee_data = fields.get("assignee")
            if not assignee_data:
                continue

            account_id = assignee_data.get("accountId")
            if account_id not in workload_map:
                workload_map[account_id] = JiraWorkloadItem(
                    user=self._parse_user(assignee_data),
                    assigned_issues=0,
                    in_progress_issues=0,
                    total_story_points=0,
                    in_progress_story_points=0,
                )

            item = workload_map[account_id]
            item.assigned_issues += 1

            points = fields.get("customfield_10016") or 0
            item.total_story_points += points

            status = fields.get("status", {}).get("statusCategory", {}).get("key", "")
            if status == "indeterminate":  # In Progress
                item.in_progress_issues += 1
                item.in_progress_story_points += points

        return list(workload_map.values())

    def _parse_issue(self, data: dict[str, Any]) -> JiraIssue:
        """Parse raw Jira issue data into schema."""
        fields = data.get("fields", {})

        return JiraIssue(
            key=data["key"],
            id=data["id"],
            summary=fields.get("summary", ""),
            description=self._get_text_from_adf(fields.get("description")),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            status=fields.get("status", {}).get("name", ""),
            priority=fields.get("priority", {}).get("name") if fields.get("priority") else None,
            assignee=self._parse_user(fields.get("assignee")),
            reporter=self._parse_user(fields.get("reporter")),
            project_key=fields.get("project", {}).get("key", ""),
            labels=fields.get("labels", []),
            components=[c.get("name", "") for c in fields.get("components", [])],
            story_points=fields.get("customfield_10016"),
            sprint=self._get_sprint_name(fields.get("sprint")),
            epic_key=fields.get("parent", {}).get("key") if fields.get("parent") else None,
            created_at=datetime.fromisoformat(fields.get("created", "").replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(fields.get("updated", "").replace("Z", "+00:00")),
            resolved_at=datetime.fromisoformat(fields.get("resolutiondate").replace("Z", "+00:00"))
            if fields.get("resolutiondate") else None,
        )

    def _parse_user(self, data: dict[str, Any] | None) -> JiraUser | None:
        """Parse user data."""
        if not data:
            return None
        return JiraUser(
            account_id=data.get("accountId", ""),
            display_name=data.get("displayName", ""),
            email=data.get("emailAddress"),
            avatar_url=data.get("avatarUrls", {}).get("48x48"),
        )

    def _get_text_from_adf(self, adf: dict[str, Any] | None) -> str | None:
        """Extract plain text from Atlassian Document Format."""
        if not adf:
            return None

        def extract_text(node: dict[str, Any]) -> str:
            if node.get("type") == "text":
                return node.get("text", "")
            content = node.get("content", [])
            return " ".join(extract_text(child) for child in content)

        return extract_text(adf).strip() or None

    def _get_sprint_name(self, sprint_data: list | None) -> str | None:
        """Get sprint name from sprint field."""
        if not sprint_data or not isinstance(sprint_data, list):
            return None
        # Get the most recent sprint
        for sprint in reversed(sprint_data):
            if isinstance(sprint, dict):
                return sprint.get("name")
        return None

    def _calculate_days_blocked(self, created: str | None) -> int:
        """Calculate days since issue was created."""
        if not created:
            return 0
        created_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return (datetime.now(created_date.tzinfo) - created_date).days


# Singleton instance
jira_connector = JiraConnector()
