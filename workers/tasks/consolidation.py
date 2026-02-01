"""Knowledge consolidation tasks for generating summaries."""

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


@app.task(bind=True, max_retries=2, default_retry_delay=600)
def generate_weekly_summaries(self):
    """Generate weekly summaries for all topics.

    Aggregates context nodes from the past week into summaries.
    """
    return run_async(_generate_weekly_summaries())


async def _generate_weekly_summaries():
    """Async implementation of weekly summary generation."""
    from src.knowledge.textbook.consolidation import consolidation_service

    logger.info("Starting weekly summary generation")

    try:
        result = await consolidation_service.consolidate_all_topics(
            summary_type="weekly"
        )

        logger.info(
            "Weekly summaries generated",
            success=result["success"],
            errors=result["errors"],
        )

        return {
            "status": "success",
            "summaries_generated": result["success"],
            "errors": result["errors"],
        }

    except Exception as e:
        logger.error("Weekly summary generation failed", error=str(e))
        return {"status": "error", "message": str(e)}


@app.task(bind=True, max_retries=2, default_retry_delay=600)
def generate_monthly_summaries(self):
    """Generate monthly summaries for all topics.

    Aggregates weekly summaries from the past month.
    """
    return run_async(_generate_monthly_summaries())


async def _generate_monthly_summaries():
    """Async implementation of monthly summary generation."""
    from src.knowledge.textbook.consolidation import consolidation_service

    logger.info("Starting monthly summary generation")

    try:
        result = await consolidation_service.consolidate_all_topics(
            summary_type="monthly"
        )

        logger.info(
            "Monthly summaries generated",
            success=result["success"],
            errors=result["errors"],
        )

        return {
            "status": "success",
            "summaries_generated": result["success"],
            "errors": result["errors"],
        }

    except Exception as e:
        logger.error("Monthly summary generation failed", error=str(e))
        return {"status": "error", "message": str(e)}


@app.task
def update_entity_importance():
    """Update importance scores for entities based on mention frequency."""
    return run_async(_update_entity_importance())


async def _update_entity_importance():
    """Async implementation of entity importance update."""
    from src.knowledge.textbook.consolidation import consolidation_service

    logger.info("Updating entity importance scores")

    try:
        updated_count = await consolidation_service.update_entity_importance()

        logger.info("Entity importance updated", count=updated_count)

        return {
            "status": "success",
            "entities_updated": updated_count,
        }

    except Exception as e:
        logger.error("Entity importance update failed", error=str(e))
        return {"status": "error", "message": str(e)}


@app.task
def generate_topic_summary(topic_id: str, summary_type: str = "weekly"):
    """Generate a summary for a specific topic."""
    return run_async(_generate_topic_summary(topic_id, summary_type))


async def _generate_topic_summary(topic_id: str, summary_type: str):
    """Async implementation of single topic summary generation."""
    from src.knowledge.textbook.consolidation import consolidation_service

    logger.info("Generating topic summary", topic_id=topic_id, type=summary_type)

    try:
        if summary_type == "weekly":
            summary = await consolidation_service.generate_weekly_summary(topic_id)
        else:
            summary = await consolidation_service.generate_monthly_summary(topic_id)

        if summary:
            return {
                "status": "success",
                "summary_id": summary.get("id"),
                "topic_id": topic_id,
            }
        else:
            return {
                "status": "skipped",
                "reason": "No content to summarize",
                "topic_id": topic_id,
            }

    except Exception as e:
        logger.error("Topic summary generation failed", topic_id=topic_id, error=str(e))
        return {"status": "error", "message": str(e)}


@app.task
def cleanup_old_contexts(days_old: int = 90):
    """Archive or remove old context nodes.

    Keeps summaries but archives individual contexts older than threshold.
    """
    return run_async(_cleanup_old_contexts(days_old))


async def _cleanup_old_contexts(days_old: int):
    """Async implementation of old context cleanup."""
    from src.knowledge.graph.client import neo4j_client

    logger.info("Cleaning up old contexts", threshold_days=days_old)

    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    try:
        # Mark old contexts as archived instead of deleting
        query = """
        MATCH (c:Context)
        WHERE c.created_at < datetime($cutoff)
          AND NOT exists(c.archived)
        SET c.archived = true
        RETURN count(c) as archived_count
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(query, cutoff=cutoff_date.isoformat())
            record = await result.single()
            archived_count = record["archived_count"] if record else 0

        logger.info("Contexts archived", count=archived_count)

        return {
            "status": "success",
            "contexts_archived": archived_count,
        }

    except Exception as e:
        logger.error("Context cleanup failed", error=str(e))
        return {"status": "error", "message": str(e)}


@app.task
def rebuild_embeddings(collection: str = "knowledge"):
    """Rebuild embeddings for all documents in a collection.

    Useful after embedding model updates.
    """
    return run_async(_rebuild_embeddings(collection))


async def _rebuild_embeddings(collection: str):
    """Async implementation of embedding rebuild."""
    from src.knowledge.graph.client import neo4j_client
    from src.knowledge.indexing.embedder import embedder

    logger.info("Rebuilding embeddings", collection=collection)

    try:
        # Get all context nodes
        query = """
        MATCH (c:Context)
        WHERE c.content IS NOT NULL
        RETURN c.id as id, c.content as content, c.title as title
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(query)
            records = await result.data()

        updated_count = 0
        error_count = 0

        for record in records:
            try:
                content = record.get("content", "")
                title = record.get("title", "")
                node_id = record.get("id")

                if content:
                    text = f"{title}\n\n{content}" if title else content

                    await embedder.store_embedding(
                        collection=collection,
                        text=text,
                        metadata={
                            "node_id": node_id,
                            "source_type": "context",
                        },
                        point_id=node_id,
                    )
                    updated_count += 1

            except Exception as e:
                logger.warning("Failed to update embedding", node_id=record.get("id"), error=str(e))
                error_count += 1

        logger.info(
            "Embeddings rebuilt",
            updated=updated_count,
            errors=error_count,
        )

        return {
            "status": "success",
            "embeddings_updated": updated_count,
            "errors": error_count,
        }

    except Exception as e:
        logger.error("Embedding rebuild failed", error=str(e))
        return {"status": "error", "message": str(e)}
