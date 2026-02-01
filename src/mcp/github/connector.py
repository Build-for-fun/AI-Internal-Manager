"""GitHub MCP Connector implementation."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from src.config import settings
from src.mcp.base import BaseMCPConnector, MCPToolParameter
from src.mcp.github.schemas import (
    GitHubCodeOwnership,
    GitHubCommit,
    GitHubPullRequest,
    GitHubReview,
    GitHubReviewStats,
    GitHubUser,
)

logger = structlog.get_logger()


class GitHubConnector(BaseMCPConnector):
    """MCP Connector for GitHub.

    Provides tools for:
    - Pull request retrieval and listing
    - Code ownership analysis
    - Activity heatmaps
    - Commit history
    - Review statistics
    """

    def __init__(self):
        super().__init__("github")
        self._client: httpx.AsyncClient | None = None
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all GitHub tools."""

        # Get PR
        self._create_tool(
            name="github_get_pr",
            description="Get details of a specific pull request",
            parameters=[
                MCPToolParameter(
                    name="repo",
                    type="string",
                    description="Repository name (owner/repo format)",
                ),
                MCPToolParameter(
                    name="pr_number",
                    type="integer",
                    description="Pull request number",
                ),
            ],
            handler=self.get_pr,
            category="github_read",
        )

        # List PRs
        self._create_tool(
            name="github_list_prs",
            description="List pull requests for a repository",
            parameters=[
                MCPToolParameter(
                    name="repo",
                    type="string",
                    description="Repository name (owner/repo format)",
                ),
                MCPToolParameter(
                    name="state",
                    type="string",
                    description="PR state filter",
                    required=False,
                    default="open",
                    enum=["open", "closed", "all"],
                ),
                MCPToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of PRs to return",
                    required=False,
                    default=30,
                ),
            ],
            handler=self.list_prs,
            category="github_read",
        )

        # Get Code Owners
        self._create_tool(
            name="github_get_code_owners",
            description="Analyze code ownership for a path in a repository",
            parameters=[
                MCPToolParameter(
                    name="repo",
                    type="string",
                    description="Repository name (owner/repo format)",
                ),
                MCPToolParameter(
                    name="path",
                    type="string",
                    description="Path to analyze (e.g., 'src/api')",
                    required=False,
                    default="",
                ),
            ],
            handler=self.get_code_owners,
            category="github_analytics",
        )

        # Get Activity Heatmap
        self._create_tool(
            name="github_get_activity_heatmap",
            description="Get activity patterns for contributors",
            parameters=[
                MCPToolParameter(
                    name="repo",
                    type="string",
                    description="Repository name (owner/repo format)",
                ),
                MCPToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze",
                    required=False,
                    default=30,
                ),
            ],
            handler=self.get_activity_heatmap,
            category="github_analytics",
        )

        # Get Commit History
        self._create_tool(
            name="github_get_commit_history",
            description="Get recent commit history for a repository",
            parameters=[
                MCPToolParameter(
                    name="repo",
                    type="string",
                    description="Repository name (owner/repo format)",
                ),
                MCPToolParameter(
                    name="author",
                    type="string",
                    description="Filter by author username",
                    required=False,
                ),
                MCPToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of commits",
                    required=False,
                    default=50,
                ),
            ],
            handler=self.get_commit_history,
            category="github_read",
        )

        # Get Review Stats
        self._create_tool(
            name="github_get_review_stats",
            description="Get review statistics for team members",
            parameters=[
                MCPToolParameter(
                    name="repo",
                    type="string",
                    description="Repository name (owner/repo format)",
                ),
                MCPToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze",
                    required=False,
                    default=30,
                ),
            ],
            handler=self.get_review_stats,
            category="github_analytics",
        )

    async def connect(self) -> None:
        """Connect to GitHub API."""
        token = settings.github_token.get_secret_value()
        if not token:
            logger.warning("GitHub token not configured")
            return

        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"Bearer {token}",
            },
            timeout=30.0,
        )
        self._connected = True
        logger.info("GitHub connector connected")

    async def disconnect(self) -> None:
        """Disconnect from GitHub API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def health_check(self) -> bool:
        """Check GitHub API health."""
        if not self._client:
            return False
        try:
            response = await self._client.get("/user")
            return response.status_code == 200
        except Exception:
            return False

    async def get_pr(self, repo: str, pr_number: int) -> GitHubPullRequest:
        """Get a specific pull request."""
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}")
        response.raise_for_status()
        data = response.json()
        return self._parse_pr(data)

    async def list_prs(
        self,
        repo: str,
        state: str = "open",
        limit: int = 30,
    ) -> list[GitHubPullRequest]:
        """List pull requests for a repository."""
        prs = []
        page = 1
        per_page = min(limit, 100)

        while len(prs) < limit:
            response = await self._client.get(
                f"/repos/{repo}/pulls",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            for pr_data in data:
                prs.append(self._parse_pr(pr_data))
                if len(prs) >= limit:
                    break

            page += 1

        return prs

    async def get_code_owners(
        self,
        repo: str,
        path: str = "",
    ) -> list[GitHubCodeOwnership]:
        """Analyze code ownership for a path."""
        # Get commits for the path
        params = {"per_page": 100}
        if path:
            params["path"] = path

        response = await self._client.get(
            f"/repos/{repo}/commits",
            params=params,
        )
        response.raise_for_status()
        commits = response.json()

        # Count commits per author
        author_commits: dict[str, dict] = defaultdict(lambda: {
            "count": 0,
            "last_date": None,
            "user": None,
        })

        for commit in commits:
            author = commit.get("author")
            if author:
                login = author.get("login", "unknown")
                author_commits[login]["count"] += 1
                author_commits[login]["user"] = self._parse_user(author)

                commit_date = datetime.fromisoformat(
                    commit["commit"]["author"]["date"].replace("Z", "+00:00")
                )
                if not author_commits[login]["last_date"] or commit_date > author_commits[login]["last_date"]:
                    author_commits[login]["last_date"] = commit_date

        # Calculate ownership percentages
        total_commits = sum(a["count"] for a in author_commits.values())
        owners = []

        for login, data in author_commits.items():
            ownership_pct = (data["count"] / total_commits * 100) if total_commits > 0 else 0
            owners.append(GitHubCodeOwnership(
                path=path or "/",
                owners=[data["user"]] if data["user"] else [],
                commit_count=data["count"],
                last_modified=data["last_date"],
                primary_owner=data["user"],
                ownership_percentage=ownership_pct,
            ))

        # Sort by commit count
        owners.sort(key=lambda x: x.commit_count, reverse=True)
        return owners

    async def get_activity_heatmap(
        self,
        repo: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get activity heatmap for contributors."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        # Get commits
        response = await self._client.get(
            f"/repos/{repo}/commits",
            params={"since": since, "per_page": 100},
        )
        response.raise_for_status()
        commits = response.json()

        # Build heatmap
        heatmap: dict[str, dict[int, dict[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

        for commit in commits:
            author = commit.get("author")
            if author:
                login = author.get("login", "unknown")
                commit_date = datetime.fromisoformat(
                    commit["commit"]["author"]["date"].replace("Z", "+00:00")
                )
                day = commit_date.weekday()
                hour = commit_date.hour
                heatmap[login][day][hour] += 1

        return {
            "period_days": days,
            "contributors": dict(heatmap),
        }

    async def get_commit_history(
        self,
        repo: str,
        author: str | None = None,
        limit: int = 50,
    ) -> list[GitHubCommit]:
        """Get commit history for a repository."""
        params = {"per_page": min(limit, 100)}
        if author:
            params["author"] = author

        response = await self._client.get(
            f"/repos/{repo}/commits",
            params=params,
        )
        response.raise_for_status()
        commits_data = response.json()

        commits = []
        for commit_data in commits_data[:limit]:
            commit = commit_data.get("commit", {})
            stats = commit_data.get("stats", {})

            commits.append(GitHubCommit(
                sha=commit_data["sha"],
                message=commit.get("message", ""),
                author=self._parse_user(commit_data.get("author")),
                committer=self._parse_user(commit_data.get("committer")),
                committed_at=datetime.fromisoformat(
                    commit["author"]["date"].replace("Z", "+00:00")
                ),
                additions=stats.get("additions", 0),
                deletions=stats.get("deletions", 0),
                files_changed=len(commit_data.get("files", [])),
                url=commit_data.get("html_url", ""),
            ))

        return commits

    async def get_review_stats(
        self,
        repo: str,
        days: int = 30,
    ) -> list[GitHubReviewStats]:
        """Get review statistics for team members."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        # Get closed PRs in the time period
        response = await self._client.get(
            f"/repos/{repo}/pulls",
            params={
                "state": "closed",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
            },
        )
        response.raise_for_status()
        prs = response.json()

        # Collect review stats
        stats: dict[str, dict] = defaultdict(lambda: {
            "user": None,
            "reviews_given": 0,
            "reviews_received": 0,
            "approvals": 0,
            "total_comments": 0,
            "review_times": [],
        })

        for pr in prs:
            pr_created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            if pr_created < datetime.fromisoformat(since.replace("Z", "+00:00")):
                continue

            author = pr.get("user", {}).get("login", "unknown")
            stats[author]["reviews_received"] += 1
            stats[author]["user"] = self._parse_user(pr.get("user"))

            # Get reviews for this PR
            reviews_response = await self._client.get(
                f"/repos/{repo}/pulls/{pr['number']}/reviews"
            )
            if reviews_response.status_code == 200:
                reviews = reviews_response.json()
                for review in reviews:
                    reviewer = review.get("user", {}).get("login", "unknown")
                    stats[reviewer]["reviews_given"] += 1
                    stats[reviewer]["user"] = self._parse_user(review.get("user"))

                    if review.get("state") == "APPROVED":
                        stats[reviewer]["approvals"] += 1

                    # Calculate review time
                    if review.get("submitted_at"):
                        review_time = datetime.fromisoformat(
                            review["submitted_at"].replace("Z", "+00:00")
                        )
                        time_diff = (review_time - pr_created).total_seconds() / 3600
                        stats[reviewer]["review_times"].append(time_diff)

        # Build result
        result = []
        for login, data in stats.items():
            if data["user"]:
                avg_time = (
                    sum(data["review_times"]) / len(data["review_times"])
                    if data["review_times"] else 0
                )
                approval_rate = (
                    data["approvals"] / data["reviews_given"]
                    if data["reviews_given"] > 0 else 0
                )

                result.append(GitHubReviewStats(
                    user=data["user"],
                    reviews_given=data["reviews_given"],
                    reviews_received=data["reviews_received"],
                    avg_review_time_hours=avg_time,
                    approval_rate=approval_rate,
                    comments_per_review=0,  # Would need additional API calls
                ))

        return result

    def _parse_pr(self, data: dict[str, Any]) -> GitHubPullRequest:
        """Parse raw PR data into schema."""
        return GitHubPullRequest(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state="merged" if data.get("merged_at") else data["state"],
            author=self._parse_user(data.get("user")),
            assignees=[self._parse_user(a) for a in data.get("assignees", []) if a],
            reviewers=[
                self._parse_user(r.get("user"))
                for r in data.get("requested_reviewers", [])
                if r and r.get("user")
            ],
            labels=[l.get("name", "") for l in data.get("labels", [])],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            merged_at=datetime.fromisoformat(data["merged_at"].replace("Z", "+00:00"))
            if data.get("merged_at") else None,
            closed_at=datetime.fromisoformat(data["closed_at"].replace("Z", "+00:00"))
            if data.get("closed_at") else None,
            commits=data.get("commits", 0),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changed_files", 0),
            review_comments=data.get("review_comments", 0),
            url=data.get("html_url", ""),
            base_branch=data.get("base", {}).get("ref", ""),
            head_branch=data.get("head", {}).get("ref", ""),
        )

    def _parse_user(self, data: dict[str, Any] | None) -> GitHubUser | None:
        """Parse user data."""
        if not data:
            return None
        return GitHubUser(
            login=data.get("login", ""),
            id=data.get("id", 0),
            avatar_url=data.get("avatar_url"),
            name=data.get("name"),
            email=data.get("email"),
        )


# Singleton instance
github_connector = GitHubConnector()
