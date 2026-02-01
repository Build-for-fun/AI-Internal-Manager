"""Celery application configuration."""

from celery import Celery

from src.config import settings

# Create Celery app
app = Celery(
    "ai_internal_manager",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "workers.tasks.ingestion",
        "workers.tasks.consolidation",
    ],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
)

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Jira ingestion - every hour
    "ingest-jira-hourly": {
        "task": "workers.tasks.ingestion.ingest_jira_data",
        "schedule": 3600,  # 1 hour
    },
    # GitHub ingestion - every 2 hours
    "ingest-github-bi-hourly": {
        "task": "workers.tasks.ingestion.ingest_github_data",
        "schedule": 7200,  # 2 hours
    },
    # Slack ingestion - every 4 hours
    "ingest-slack-4-hourly": {
        "task": "workers.tasks.ingestion.ingest_slack_data",
        "schedule": 14400,  # 4 hours
    },
    # Weekly consolidation - Sundays at 2 AM
    "consolidate-weekly": {
        "task": "workers.tasks.consolidation.generate_weekly_summaries",
        "schedule": {
            "crontab": {
                "minute": 0,
                "hour": 2,
                "day_of_week": 0,  # Sunday
            },
        },
    },
    # Monthly consolidation - 1st of month at 3 AM
    "consolidate-monthly": {
        "task": "workers.tasks.consolidation.generate_monthly_summaries",
        "schedule": {
            "crontab": {
                "minute": 0,
                "hour": 3,
                "day_of_month": 1,
            },
        },
    },
    # Entity importance update - daily at 4 AM
    "update-entity-importance": {
        "task": "workers.tasks.consolidation.update_entity_importance",
        "schedule": {
            "crontab": {
                "minute": 0,
                "hour": 4,
            },
        },
    },
}

if __name__ == "__main__":
    app.start()
