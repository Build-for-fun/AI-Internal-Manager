"""Celery beat schedules for periodic tasks."""

from celery.schedules import crontab

# Schedule definitions
# These are imported into celery_app.py

SCHEDULES = {
    # ========== Ingestion Tasks ==========

    # Jira: Every hour at minute 0
    "ingest-jira-hourly": {
        "task": "workers.tasks.ingestion.ingest_jira_data",
        "schedule": crontab(minute=0),
        "options": {"queue": "ingestion"},
    },

    # GitHub: Every 2 hours at minute 15
    "ingest-github-bi-hourly": {
        "task": "workers.tasks.ingestion.ingest_github_data",
        "schedule": crontab(minute=15, hour="*/2"),
        "options": {"queue": "ingestion"},
    },

    # Slack: Every 4 hours at minute 30
    "ingest-slack-4-hourly": {
        "task": "workers.tasks.ingestion.ingest_slack_data",
        "schedule": crontab(minute=30, hour="*/4"),
        "options": {"queue": "ingestion"},
    },

    # ========== Consolidation Tasks ==========

    # Weekly summaries: Sunday at 2 AM
    "consolidate-weekly": {
        "task": "workers.tasks.consolidation.generate_weekly_summaries",
        "schedule": crontab(minute=0, hour=2, day_of_week=0),
        "options": {"queue": "consolidation"},
    },

    # Monthly summaries: 1st of month at 3 AM
    "consolidate-monthly": {
        "task": "workers.tasks.consolidation.generate_monthly_summaries",
        "schedule": crontab(minute=0, hour=3, day_of_month=1),
        "options": {"queue": "consolidation"},
    },

    # Entity importance: Daily at 4 AM
    "update-entity-importance": {
        "task": "workers.tasks.consolidation.update_entity_importance",
        "schedule": crontab(minute=0, hour=4),
        "options": {"queue": "consolidation"},
    },

    # ========== Maintenance Tasks ==========

    # Cleanup old contexts: Weekly on Saturday at 1 AM
    "cleanup-old-contexts": {
        "task": "workers.tasks.consolidation.cleanup_old_contexts",
        "schedule": crontab(minute=0, hour=1, day_of_week=6),
        "args": (90,),  # 90 days threshold
        "options": {"queue": "maintenance"},
    },
}


def get_schedules():
    """Get all schedules for Celery beat."""
    return SCHEDULES
