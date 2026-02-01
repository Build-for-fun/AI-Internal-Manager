"""Data ingestion tasks for Jira, GitHub, and Slack."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog

from workers.celery_app import app

logger = structlog.get_logger()


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def ingest_jira_data(self, project_keys: list[str] | None = None):
    """Ingest data from Jira.

    Fetches issues updated in the last hour, normalizes them,
    and stores in the knowledge graph.
    """
    return run_async(_ingest_jira_data(project_keys))


async def _ingest_jira_data(project_keys: list[str] | None = None):
    """Async implementation of Jira ingestion."""
    from src.knowledge.indexing.embedder import embedder
    from src.knowledge.textbook.hierarchy import hierarchy_manager
    from src.mcp.jira.connector import jira_connector

    logger.info("Starting Jira ingestion")

    # Connect if needed
    if not jira_connector.is_connected:
        try:
            await jira_connector.connect()
        except Exception as e:
            logger.error("Failed to connect to Jira", error=str(e))
            return {"status": "error", "message": str(e)}

    # Get recently updated issues
    since = datetime.utcnow() - timedelta(hours=2)
    since_str = since.strftime("%Y-%m-%d %H:%M")

    jql = f'updated >= "{since_str}"'
    if project_keys:
        projects = ",".join(project_keys)
        jql = f'project IN ({projects}) AND {jql}'

    try:
        issues = await jira_connector.search_issues(jql, max_results=100)
    except Exception as e:
        logger.error("Failed to fetch Jira issues", error=str(e))
        return {"status": "error", "message": str(e)}

    ingested_count = 0
    error_count = 0

    for issue in issues:
        try:
            # Determine hierarchy path
            # Use project and issue type to determine department/topic
            department = "Engineering"  # Would map from project
            subdepartment = issue.project_key
            topic = issue.issue_type

            # Find or create path
            path = await hierarchy_manager.find_or_create_path(
                department_name=department,
                subdepartment_name=subdepartment,
                topic_name=topic,
            )

            topic_id = path.get("topic_id")
            if not topic_id:
                logger.warning("Could not find/create topic", issue=issue.key)
                continue

            # Create context content
            content = f"""
Issue: {issue.key}
Summary: {issue.summary}
Status: {issue.status}
Priority: {issue.priority or 'None'}
Assignee: {issue.assignee.display_name if issue.assignee else 'Unassigned'}

Description:
{issue.description or 'No description'}
"""

            # Add context to knowledge graph
            context = await hierarchy_manager.add_context(
                topic_id=topic_id,
                title=f"{issue.key}: {issue.summary}",
                content=content,
                source_type="jira",
                source_id=issue.key,
                source_url=f"https://jira.example.com/browse/{issue.key}",
                importance=0.7 if issue.priority == "High" else 0.5,
                metadata={
                    "status": issue.status,
                    "priority": issue.priority,
                    "assignee": issue.assignee.display_name if issue.assignee else None,
                    "labels": issue.labels,
                    "story_points": issue.story_points,
                },
            )

            # Store embedding
            await embedder.store_embedding(
                collection="knowledge",
                text=content,
                metadata={
                    "source_type": "jira",
                    "source_id": issue.key,
                    "node_id": context.get("id"),
                    "topic_id": topic_id,
                    "department": department,
                },
                point_id=context.get("id"),
            )

            ingested_count += 1

        except Exception as e:
            logger.error("Failed to ingest issue", issue=issue.key, error=str(e))
            error_count += 1

    logger.info(
        "Jira ingestion completed",
        ingested=ingested_count,
        errors=error_count,
    )

    return {
        "status": "success",
        "ingested": ingested_count,
        "errors": error_count,
    }


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def ingest_github_data(self, repos: list[str] | None = None):
    """Ingest data from GitHub.

    Fetches recent PRs and commits, normalizes them,
    and stores in the knowledge graph.
    """
    return run_async(_ingest_github_data(repos))


async def _ingest_github_data(repos: list[str] | None = None):
    """Async implementation of GitHub ingestion."""
    from src.knowledge.indexing.embedder import embedder
    from src.knowledge.textbook.hierarchy import hierarchy_manager
    from src.mcp.github.connector import github_connector

    logger.info("Starting GitHub ingestion")

    if not github_connector.is_connected:
        try:
            await github_connector.connect()
        except Exception as e:
            logger.error("Failed to connect to GitHub", error=str(e))
            return {"status": "error", "message": str(e)}

    # Default repos to ingest
    repos = repos or ["company/main-repo", "company/api", "company/frontend"]

    ingested_count = 0
    error_count = 0

    for repo in repos:
        try:
            # Get recent PRs
            prs = await github_connector.list_prs(repo, state="all", limit=20)

            for pr in prs:
                # Only ingest recently updated
                if pr.updated_at < datetime.utcnow() - timedelta(hours=4):
                    continue

                # Determine hierarchy
                department = "Engineering"
                subdepartment = repo.split("/")[-1]
                topic = "Pull Requests"

                path = await hierarchy_manager.find_or_create_path(
                    department_name=department,
                    subdepartment_name=subdepartment,
                    topic_name=topic,
                )

                topic_id = path.get("topic_id")
                if not topic_id:
                    continue

                # Create content
                content = f"""
PR #{pr.number}: {pr.title}
Repository: {repo}
Author: {pr.author.login if pr.author else 'Unknown'}
State: {pr.state}
Branch: {pr.head_branch} -> {pr.base_branch}
Changes: +{pr.additions} -{pr.deletions} ({pr.changed_files} files)

Description:
{pr.body or 'No description'}
"""

                context = await hierarchy_manager.add_context(
                    topic_id=topic_id,
                    title=f"PR #{pr.number}: {pr.title}",
                    content=content,
                    source_type="github",
                    source_id=f"{repo}#{pr.number}",
                    source_url=pr.url,
                    importance=0.6 if pr.state == "merged" else 0.5,
                    metadata={
                        "repo": repo,
                        "pr_number": pr.number,
                        "state": pr.state,
                        "author": pr.author.login if pr.author else None,
                        "labels": pr.labels,
                    },
                )

                # Store embedding
                await embedder.store_embedding(
                    collection="knowledge",
                    text=content,
                    metadata={
                        "source_type": "github",
                        "source_id": f"{repo}#{pr.number}",
                        "node_id": context.get("id"),
                        "topic_id": topic_id,
                    },
                    point_id=context.get("id"),
                )

                ingested_count += 1

        except Exception as e:
            logger.error("Failed to ingest from repo", repo=repo, error=str(e))
            error_count += 1

    logger.info(
        "GitHub ingestion completed",
        ingested=ingested_count,
        errors=error_count,
    )

    return {
        "status": "success",
        "ingested": ingested_count,
        "errors": error_count,
    }


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def ingest_slack_data(self, channel_ids: list[str] | None = None):
    """Ingest data from Slack.

    Fetches recent messages, extracts topics and decisions,
    and stores in the knowledge graph.
    """
    return run_async(_ingest_slack_data(channel_ids))


async def _ingest_slack_data(channel_ids: list[str] | None = None):
    """Async implementation of Slack ingestion."""
    from src.knowledge.indexing.embedder import embedder
    from src.knowledge.textbook.hierarchy import hierarchy_manager
    from src.mcp.slack.connector import slack_connector

    logger.info("Starting Slack ingestion")

    if not slack_connector.is_connected:
        try:
            await slack_connector.connect()
        except Exception as e:
            logger.error("Failed to connect to Slack", error=str(e))
            return {"status": "error", "message": str(e)}

    # Default channels
    channel_ids = channel_ids or ["engineering", "platform", "general"]

    ingested_count = 0
    error_count = 0

    for channel_id in channel_ids:
        try:
            # Get topic clusters
            clusters = await slack_connector.get_topic_clusters(channel_id, days=1)

            for cluster in clusters:
                # Determine hierarchy
                department = "General"  # Would map from channel
                subdepartment = channel_id
                topic = "Discussions"

                path = await hierarchy_manager.find_or_create_path(
                    department_name=department,
                    subdepartment_name=subdepartment,
                    topic_name=topic,
                )

                topic_id = path.get("topic_id")
                if not topic_id:
                    continue

                # Create content from cluster
                participants = ", ".join([p.name for p in cluster.participants[:5]])
                content = f"""
Topic: {cluster.topic}
Channel: {channel_id}
Messages: {cluster.message_count}
Participants: {participants}
Period: {cluster.start_time} - {cluster.end_time}

Summary:
{cluster.summary}

Keywords: {", ".join(cluster.keywords)}
"""

                context = await hierarchy_manager.add_context(
                    topic_id=topic_id,
                    title=f"Discussion: {cluster.topic[:50]}",
                    content=content,
                    source_type="slack",
                    source_id=f"{channel_id}_{cluster.start_time.timestamp()}",
                    importance=0.5,
                    metadata={
                        "channel": channel_id,
                        "message_count": cluster.message_count,
                        "keywords": cluster.keywords,
                    },
                )

                # Store embedding
                await embedder.store_embedding(
                    collection="knowledge",
                    text=content,
                    metadata={
                        "source_type": "slack",
                        "source_id": context.get("id"),
                        "node_id": context.get("id"),
                        "channel": channel_id,
                    },
                    point_id=context.get("id"),
                )

                ingested_count += 1

            # Extract decisions
            decisions = await slack_connector.extract_decisions(channel_id, days=1)

            for decision in decisions:
                # Store decisions in a separate topic
                path = await hierarchy_manager.find_or_create_path(
                    department_name=department,
                    subdepartment_name=subdepartment,
                    topic_name="Decisions",
                )

                topic_id = path.get("topic_id")
                if not topic_id:
                    continue

                content = f"""
Decision: {decision.decision}
Channel: {channel_id}
Made by: {decision.decision_maker.name if decision.decision_maker else 'Unknown'}
Date: {decision.made_at}

Context:
{decision.context}
"""

                context = await hierarchy_manager.add_context(
                    topic_id=topic_id,
                    title=f"Decision: {decision.decision[:50]}",
                    content=content,
                    source_type="slack",
                    source_id=f"decision_{decision.made_at.timestamp()}",
                    importance=0.8,  # Decisions are important
                    metadata={
                        "channel": channel_id,
                        "decision_maker": decision.decision_maker.name if decision.decision_maker else None,
                    },
                )

                # Store embedding
                await embedder.store_embedding(
                    collection="knowledge",
                    text=content,
                    metadata={
                        "source_type": "slack",
                        "type": "decision",
                        "node_id": context.get("id"),
                        "channel": channel_id,
                    },
                    point_id=context.get("id"),
                )

                ingested_count += 1

        except Exception as e:
            logger.error("Failed to ingest from channel", channel=channel_id, error=str(e))
            error_count += 1

    logger.info(
        "Slack ingestion completed",
        ingested=ingested_count,
        errors=error_count,
    )

    return {
        "status": "success",
        "ingested": ingested_count,
        "errors": error_count,
    }


@app.task
def ingest_all():
    """Run all ingestion tasks."""
    jira_result = ingest_jira_data.delay()
    github_result = ingest_github_data.delay()
    slack_result = ingest_slack_data.delay()

    return {
        "jira_task_id": jira_result.id,
        "github_task_id": github_result.id,
        "slack_task_id": slack_result.id,
    }
