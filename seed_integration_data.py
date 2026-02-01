#!/usr/bin/env python3
"""
Seed synthetic data for Jira, Slack, and GitHub integrations.
This creates sample data that simulates what the MCP connectors would return.
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import structlog

from src.config import settings
from src.knowledge.graph.client import neo4j_client

logger = structlog.get_logger()

# Sample Jira Data
SAMPLE_JIRA_SPRINTS = [
    {
        "id": "sprint-42",
        "name": "Sprint 42 - Auth Improvements",
        "state": "active",
        "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "goal": "Improve OAuth security and add MFA support",
        "team": "Platform",
    },
    {
        "id": "sprint-41",
        "name": "Sprint 41 - API Performance",
        "state": "closed",
        "start_date": (datetime.utcnow() - timedelta(days=21)).isoformat(),
        "end_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "goal": "Reduce API latency by 30%",
        "team": "Platform",
        "velocity": 34,
    },
]

SAMPLE_JIRA_ISSUES = [
    {
        "id": "jira-PLAT-1234",
        "key": "PLAT-1234",
        "summary": "Implement OAuth 2.0 PKCE flow",
        "description": "Add PKCE (Proof Key for Code Exchange) to our OAuth implementation for improved security with public clients.",
        "status": "In Progress",
        "priority": "High",
        "assignee": "alice.chen@company.com",
        "reporter": "emma.wilson@company.com",
        "sprint_id": "sprint-42",
        "story_points": 8,
        "labels": ["security", "oauth", "authentication"],
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
    {
        "id": "jira-PLAT-1235",
        "key": "PLAT-1235",
        "summary": "Add MFA support for admin users",
        "description": "Implement multi-factor authentication using TOTP for admin dashboard access.",
        "status": "To Do",
        "priority": "High",
        "assignee": "carol.williams@company.com",
        "reporter": "emma.wilson@company.com",
        "sprint_id": "sprint-42",
        "story_points": 5,
        "labels": ["security", "mfa", "admin"],
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
    },
    {
        "id": "jira-PLAT-1230",
        "key": "PLAT-1230",
        "summary": "Optimize database connection pooling",
        "description": "Reduce connection overhead by implementing proper connection pooling with asyncpg.",
        "status": "Done",
        "priority": "Medium",
        "assignee": "alice.chen@company.com",
        "reporter": "bob.smith@company.com",
        "sprint_id": "sprint-41",
        "story_points": 5,
        "labels": ["performance", "database"],
        "created_at": (datetime.utcnow() - timedelta(days=15)).isoformat(),
        "resolved_at": (datetime.utcnow() - timedelta(days=8)).isoformat(),
    },
    {
        "id": "jira-PLAT-1231",
        "key": "PLAT-1231",
        "summary": "Add Redis caching for session data",
        "description": "Implement Redis-based session caching to reduce database load.",
        "status": "Done",
        "priority": "Medium",
        "assignee": "carol.williams@company.com",
        "reporter": "alice.chen@company.com",
        "sprint_id": "sprint-41",
        "story_points": 3,
        "labels": ["performance", "caching", "redis"],
        "created_at": (datetime.utcnow() - timedelta(days=14)).isoformat(),
        "resolved_at": (datetime.utcnow() - timedelta(days=9)).isoformat(),
    },
    {
        "id": "jira-PLAT-1236",
        "key": "PLAT-1236",
        "summary": "Fix JWT token refresh race condition",
        "description": "Address race condition when multiple tabs try to refresh tokens simultaneously.",
        "status": "In Review",
        "priority": "Critical",
        "assignee": "alice.chen@company.com",
        "reporter": "carol.williams@company.com",
        "sprint_id": "sprint-42",
        "story_points": 3,
        "labels": ["bug", "jwt", "authentication"],
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
    },
    {
        "id": "jira-ML-456",
        "key": "ML-456",
        "summary": "Implement model versioning for A/B testing",
        "description": "Add support for running multiple model versions in production for A/B testing.",
        "status": "In Progress",
        "priority": "High",
        "assignee": "david.lee@company.com",
        "reporter": "emma.wilson@company.com",
        "sprint_id": "sprint-42",
        "story_points": 13,
        "labels": ["ml", "infrastructure", "testing"],
        "created_at": (datetime.utcnow() - timedelta(days=4)).isoformat(),
    },
]

# Sample GitHub Data
SAMPLE_GITHUB_REPOS = [
    {
        "id": "repo-platform-api",
        "name": "platform-api",
        "full_name": "company/platform-api",
        "description": "Core platform API service",
        "language": "Python",
        "default_branch": "main",
        "stars": 42,
        "open_issues": 12,
        "team": "Platform",
    },
    {
        "id": "repo-frontend",
        "name": "frontend",
        "full_name": "company/frontend",
        "description": "Next.js frontend application",
        "language": "TypeScript",
        "default_branch": "main",
        "stars": 28,
        "open_issues": 8,
        "team": "Platform",
    },
    {
        "id": "repo-ml-platform",
        "name": "ml-platform",
        "full_name": "company/ml-platform",
        "description": "Machine learning platform and pipelines",
        "language": "Python",
        "default_branch": "main",
        "stars": 35,
        "open_issues": 5,
        "team": "ML Platform",
    },
]

SAMPLE_GITHUB_PRS = [
    {
        "id": "pr-platform-api-342",
        "number": 342,
        "title": "feat: Add PKCE support to OAuth flow",
        "description": "Implements PKCE (RFC 7636) for improved OAuth security with public clients.",
        "state": "open",
        "author": "alice.chen",
        "repo": "platform-api",
        "base_branch": "main",
        "head_branch": "feature/oauth-pkce",
        "additions": 245,
        "deletions": 32,
        "changed_files": 8,
        "reviewers": ["carol.williams", "emma.wilson"],
        "labels": ["security", "enhancement"],
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "jira_key": "PLAT-1234",
    },
    {
        "id": "pr-platform-api-341",
        "number": 341,
        "title": "fix: Resolve JWT refresh race condition",
        "description": "Adds mutex lock to prevent concurrent token refresh attempts.",
        "state": "open",
        "author": "alice.chen",
        "repo": "platform-api",
        "base_branch": "main",
        "head_branch": "fix/jwt-race-condition",
        "additions": 78,
        "deletions": 12,
        "changed_files": 3,
        "reviewers": ["carol.williams"],
        "labels": ["bug", "critical"],
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "jira_key": "PLAT-1236",
    },
    {
        "id": "pr-platform-api-340",
        "number": 340,
        "title": "perf: Optimize connection pooling",
        "description": "Implements connection pooling with asyncpg for better performance.",
        "state": "merged",
        "author": "alice.chen",
        "repo": "platform-api",
        "base_branch": "main",
        "head_branch": "perf/connection-pooling",
        "additions": 156,
        "deletions": 89,
        "changed_files": 5,
        "reviewers": ["carol.williams", "bob.smith"],
        "labels": ["performance"],
        "created_at": (datetime.utcnow() - timedelta(days=10)).isoformat(),
        "merged_at": (datetime.utcnow() - timedelta(days=8)).isoformat(),
        "jira_key": "PLAT-1230",
    },
    {
        "id": "pr-ml-platform-89",
        "number": 89,
        "title": "feat: Model versioning infrastructure",
        "description": "Adds support for deploying and managing multiple model versions.",
        "state": "open",
        "author": "david.lee",
        "repo": "ml-platform",
        "base_branch": "main",
        "head_branch": "feature/model-versioning",
        "additions": 523,
        "deletions": 45,
        "changed_files": 12,
        "reviewers": ["alice.chen", "emma.wilson"],
        "labels": ["feature", "infrastructure"],
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "jira_key": "ML-456",
    },
]

SAMPLE_GITHUB_COMMITS = [
    {
        "id": "commit-abc123",
        "sha": "abc123def456",
        "message": "feat(oauth): Add PKCE code verifier generation",
        "author": "alice.chen",
        "repo": "platform-api",
        "pr_number": 342,
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
    },
    {
        "id": "commit-def456",
        "sha": "def456ghi789",
        "message": "test(oauth): Add PKCE flow integration tests",
        "author": "alice.chen",
        "repo": "platform-api",
        "pr_number": 342,
        "created_at": (datetime.utcnow() - timedelta(days=1, hours=12)).isoformat(),
    },
    {
        "id": "commit-ghi789",
        "sha": "ghi789jkl012",
        "message": "fix(jwt): Add mutex lock for token refresh",
        "author": "alice.chen",
        "repo": "platform-api",
        "pr_number": 341,
        "created_at": (datetime.utcnow() - timedelta(hours=18)).isoformat(),
    },
]

# Sample Slack Data
SAMPLE_SLACK_CHANNELS = [
    {
        "id": "slack-channel-engineering",
        "name": "engineering",
        "description": "General engineering discussions",
        "member_count": 25,
        "is_private": False,
        "team": "Engineering",
    },
    {
        "id": "slack-channel-platform",
        "name": "platform-team",
        "description": "Platform team coordination",
        "member_count": 8,
        "is_private": False,
        "team": "Platform",
    },
    {
        "id": "slack-channel-incidents",
        "name": "incidents",
        "description": "Production incident coordination",
        "member_count": 30,
        "is_private": False,
        "team": "Engineering",
    },
    {
        "id": "slack-channel-ml-platform",
        "name": "ml-platform",
        "description": "ML platform team discussions",
        "member_count": 10,
        "is_private": False,
        "team": "ML Platform",
    },
]

SAMPLE_SLACK_MESSAGES = [
    {
        "id": "slack-msg-001",
        "channel_id": "slack-channel-platform",
        "author": "alice.chen",
        "content": "Hey team, I've opened PR #342 for the PKCE implementation. Would appreciate reviews from @carol.williams and @emma.wilson",
        "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "thread_replies": 3,
        "reactions": ["eyes", "thumbsup"],
    },
    {
        "id": "slack-msg-002",
        "channel_id": "slack-channel-platform",
        "author": "carol.williams",
        "content": "I'll take a look this afternoon. The approach looks good from the JIRA description.",
        "timestamp": (datetime.utcnow() - timedelta(days=2, hours=-2)).isoformat(),
        "thread_parent": "slack-msg-001",
    },
    {
        "id": "slack-msg-003",
        "channel_id": "slack-channel-incidents",
        "author": "carol.williams",
        "content": "🚨 We're seeing elevated error rates on the auth service. Investigating now.",
        "timestamp": (datetime.utcnow() - timedelta(days=1, hours=5)).isoformat(),
        "thread_replies": 8,
        "reactions": ["eyes", "fire"],
        "is_incident": True,
    },
    {
        "id": "slack-msg-004",
        "channel_id": "slack-channel-incidents",
        "author": "alice.chen",
        "content": "Found the issue - it's the JWT refresh race condition. I have a fix ready in PR #341",
        "timestamp": (datetime.utcnow() - timedelta(days=1, hours=4)).isoformat(),
        "thread_parent": "slack-msg-003",
    },
    {
        "id": "slack-msg-005",
        "channel_id": "slack-channel-incidents",
        "author": "emma.wilson",
        "content": "Great catch! Let's prioritize getting that reviewed and merged. Marking PLAT-1236 as Critical.",
        "timestamp": (datetime.utcnow() - timedelta(days=1, hours=3)).isoformat(),
        "thread_parent": "slack-msg-003",
    },
    {
        "id": "slack-msg-006",
        "channel_id": "slack-channel-engineering",
        "author": "emma.wilson",
        "content": "Sprint 42 planning complete! Main focus areas: OAuth security improvements and MFA implementation. Check JIRA for your assigned stories.",
        "timestamp": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "reactions": ["thumbsup", "rocket"],
    },
    {
        "id": "slack-msg-007",
        "channel_id": "slack-channel-ml-platform",
        "author": "david.lee",
        "content": "I've started work on the model versioning infrastructure. The PR is up at #89 - this will enable A/B testing for model deployments.",
        "timestamp": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "thread_replies": 5,
        "reactions": ["rocket", "brain"],
    },
]

SAMPLE_SLACK_DECISIONS = [
    {
        "id": "slack-decision-001",
        "channel_id": "slack-channel-platform",
        "title": "Use PKCE for all OAuth public clients",
        "content": "Team agreed to implement PKCE (RFC 7636) for all public OAuth clients to improve security.",
        "decision_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
        "participants": ["alice.chen", "carol.williams", "emma.wilson"],
        "status": "approved",
    },
    {
        "id": "slack-decision-002",
        "channel_id": "slack-channel-engineering",
        "title": "Adopt asyncpg for PostgreSQL connections",
        "content": "Moving from psycopg2 to asyncpg for better async performance. All new services should use asyncpg.",
        "decision_date": (datetime.utcnow() - timedelta(days=20)).isoformat(),
        "participants": ["alice.chen", "bob.smith", "carol.williams"],
        "status": "approved",
    },
]

# Team Metrics
SAMPLE_TEAM_METRICS = [
    {
        "id": "metrics-platform-current",
        "team": "Platform",
        "sprint": "sprint-42",
        "velocity": 21,
        "committed_points": 24,
        "completed_points": 11,
        "bugs_fixed": 1,
        "prs_merged": 3,
        "code_review_time_avg_hours": 4.2,
        "deployment_frequency": "daily",
        "incident_count": 1,
        "timestamp": datetime.utcnow().isoformat(),
    },
    {
        "id": "metrics-platform-prev",
        "team": "Platform",
        "sprint": "sprint-41",
        "velocity": 34,
        "committed_points": 36,
        "completed_points": 34,
        "bugs_fixed": 2,
        "prs_merged": 12,
        "code_review_time_avg_hours": 3.8,
        "deployment_frequency": "daily",
        "incident_count": 0,
        "timestamp": (datetime.utcnow() - timedelta(days=14)).isoformat(),
    },
    {
        "id": "metrics-ml-current",
        "team": "ML Platform",
        "sprint": "sprint-42",
        "velocity": 18,
        "committed_points": 21,
        "completed_points": 8,
        "bugs_fixed": 0,
        "prs_merged": 2,
        "code_review_time_avg_hours": 6.5,
        "deployment_frequency": "weekly",
        "incident_count": 0,
        "timestamp": datetime.utcnow().isoformat(),
    },
]


async def seed_jira_data():
    """Seed Jira-related data into Neo4j."""
    logger.info("Seeding Jira data...")

    # Create Sprint nodes
    for sprint in SAMPLE_JIRA_SPRINTS:
        await neo4j_client.create_or_update_node(
            node_type="Sprint",
            properties=sprint,
        )
    logger.info(f"Created {len(SAMPLE_JIRA_SPRINTS)} sprints")

    # Create Issue nodes
    for issue in SAMPLE_JIRA_ISSUES:
        await neo4j_client.create_or_update_node(
            node_type="JiraIssue",
            properties=issue,
        )
        # Link to sprint
        if issue.get("sprint_id"):
            await neo4j_client.create_relationship_by_type(
                from_type="Sprint",
                from_id=issue["sprint_id"],
                to_type="JiraIssue",
                to_id=issue["id"],
                relationship_type="CONTAINS_ISSUE",
            )
        # Link to assignee (Person node)
        if issue.get("assignee"):
            person_id = f"person-{issue['assignee'].split('@')[0]}"
            await neo4j_client.create_or_update_node(
                node_type="Person",
                properties={
                    "id": person_id,
                    "email": issue["assignee"],
                    "name": issue["assignee"].split("@")[0].replace(".", " ").title(),
                },
            )
            await neo4j_client.create_relationship_by_type(
                from_type="Person",
                from_id=person_id,
                to_type="JiraIssue",
                to_id=issue["id"],
                relationship_type="ASSIGNED_TO",
            )
    logger.info(f"Created {len(SAMPLE_JIRA_ISSUES)} Jira issues")


async def seed_github_data():
    """Seed GitHub-related data into Neo4j."""
    logger.info("Seeding GitHub data...")

    # Create Repository nodes
    for repo in SAMPLE_GITHUB_REPOS:
        await neo4j_client.create_or_update_node(
            node_type="Repository",
            properties=repo,
        )
    logger.info(f"Created {len(SAMPLE_GITHUB_REPOS)} repositories")

    # Create Pull Request nodes
    for pr in SAMPLE_GITHUB_PRS:
        await neo4j_client.create_or_update_node(
            node_type="PullRequest",
            properties=pr,
        )
        # Link to repository
        repo_id = f"repo-{pr['repo']}"
        await neo4j_client.create_relationship_by_type(
            from_type="Repository",
            from_id=repo_id,
            to_type="PullRequest",
            to_id=pr["id"],
            relationship_type="HAS_PR",
        )
        # Link to Jira issue if exists
        if pr.get("jira_key"):
            jira_id = f"jira-{pr['jira_key']}"
            try:
                await neo4j_client.create_relationship_by_type(
                    from_type="PullRequest",
                    from_id=pr["id"],
                    to_type="JiraIssue",
                    to_id=jira_id,
                    relationship_type="IMPLEMENTS",
                )
            except Exception:
                pass  # Jira issue might not exist
    logger.info(f"Created {len(SAMPLE_GITHUB_PRS)} pull requests")

    # Create Commit nodes
    for commit in SAMPLE_GITHUB_COMMITS:
        await neo4j_client.create_or_update_node(
            node_type="Commit",
            properties=commit,
        )
        # Link to PR
        pr_id = f"pr-{commit['repo']}-{commit['pr_number']}"
        try:
            await neo4j_client.create_relationship_by_type(
                from_type="PullRequest",
                from_id=pr_id,
                to_type="Commit",
                to_id=commit["id"],
                relationship_type="CONTAINS_COMMIT",
            )
        except Exception:
            pass
    logger.info(f"Created {len(SAMPLE_GITHUB_COMMITS)} commits")


async def seed_slack_data():
    """Seed Slack-related data into Neo4j."""
    logger.info("Seeding Slack data...")

    # Create Channel nodes
    for channel in SAMPLE_SLACK_CHANNELS:
        await neo4j_client.create_or_update_node(
            node_type="SlackChannel",
            properties=channel,
        )
    logger.info(f"Created {len(SAMPLE_SLACK_CHANNELS)} Slack channels")

    # Create Message nodes
    for msg in SAMPLE_SLACK_MESSAGES:
        await neo4j_client.create_or_update_node(
            node_type="SlackMessage",
            properties=msg,
        )
        # Link to channel
        await neo4j_client.create_relationship_by_type(
            from_type="SlackChannel",
            from_id=msg["channel_id"],
            to_type="SlackMessage",
            to_id=msg["id"],
            relationship_type="CONTAINS_MESSAGE",
        )
    logger.info(f"Created {len(SAMPLE_SLACK_MESSAGES)} Slack messages")

    # Create Decision nodes from Slack
    for decision in SAMPLE_SLACK_DECISIONS:
        await neo4j_client.create_or_update_node(
            node_type="Decision",
            properties={
                **decision,
                "source": "slack",
            },
        )
    logger.info(f"Created {len(SAMPLE_SLACK_DECISIONS)} Slack decisions")


async def seed_team_metrics():
    """Seed team metrics data into Neo4j."""
    logger.info("Seeding team metrics...")

    for metrics in SAMPLE_TEAM_METRICS:
        await neo4j_client.create_or_update_node(
            node_type="TeamMetrics",
            properties=metrics,
        )
    logger.info(f"Created {len(SAMPLE_TEAM_METRICS)} team metrics records")


async def main():
    """Run all integration data seeding operations."""
    logger.info("Starting integration data seeding (Jira, GitHub, Slack)...")

    try:
        # Connect to Neo4j
        await neo4j_client.connect()

        # Seed all integration data
        await seed_jira_data()
        await seed_github_data()
        await seed_slack_data()
        await seed_team_metrics()

        logger.info("✅ Integration data seeding complete!")
        logger.info("Sample data includes:")
        logger.info(f"  - {len(SAMPLE_JIRA_SPRINTS)} sprints")
        logger.info(f"  - {len(SAMPLE_JIRA_ISSUES)} Jira issues")
        logger.info(f"  - {len(SAMPLE_GITHUB_REPOS)} repositories")
        logger.info(f"  - {len(SAMPLE_GITHUB_PRS)} pull requests")
        logger.info(f"  - {len(SAMPLE_GITHUB_COMMITS)} commits")
        logger.info(f"  - {len(SAMPLE_SLACK_CHANNELS)} Slack channels")
        logger.info(f"  - {len(SAMPLE_SLACK_MESSAGES)} Slack messages")
        logger.info(f"  - {len(SAMPLE_TEAM_METRICS)} team metrics records")

    except Exception as e:
        logger.error("Error during integration data seeding", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
