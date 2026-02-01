"""Knowledge consolidation for creating summaries.

This module handles the periodic consolidation of context nodes into summaries:
- Weekly summaries aggregate context from the past week
- Monthly summaries aggregate weekly summaries
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.config import settings
from src.knowledge.graph.client import neo4j_client
from src.knowledge.graph.schema import NodeLabels, RelationshipTypes

logger = structlog.get_logger()


class ConsolidationService:
    """Service for consolidating knowledge into summaries."""

    def __init__(self):
        self.llm_provider = settings.llm_provider
        if self.llm_provider == "keywords_ai":
            self.client = AsyncOpenAI(
                api_key=settings.keywords_ai_api_key.get_secret_value(),
                base_url=settings.keywords_ai_base_url,
            )
            self.model = settings.keywords_ai_default_model
        else:
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
            self.model = settings.anthropic_default_model

    async def generate_weekly_summary(
        self,
        topic_id: str,
        end_date: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Generate a weekly summary for a topic.

        Aggregates all context nodes from the past week and generates
        a concise summary using Claude.
        """
        end_date = end_date or datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # Get contexts from the past week
        contexts = await self._get_contexts_in_period(topic_id, start_date, end_date)

        if not contexts:
            logger.info("No contexts to summarize", topic_id=topic_id)
            return None

        # Get topic info for context
        topic = await neo4j_client.get_node(topic_id, NodeLabels.TOPIC)
        if not topic:
            logger.error("Topic not found", topic_id=topic_id)
            return None

        # Generate summary using Claude
        summary_content = await self._generate_summary_with_llm(
            topic_title=topic.get("title", ""),
            topic_description=topic.get("description", ""),
            contexts=contexts,
            summary_type="weekly",
        )

        # Create summary node
        summary = await self._create_summary_node(
            topic_id=topic_id,
            title=f"Weekly Summary: {topic.get('title')} ({start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')})",
            content=summary_content,
            summary_type="weekly",
            period_start=start_date,
            period_end=end_date,
            source_context_ids=[c["id"] for c in contexts],
        )

        logger.info(
            "Generated weekly summary",
            topic_id=topic_id,
            summary_id=summary.get("id"),
            context_count=len(contexts),
        )

        return summary

    async def generate_monthly_summary(
        self,
        topic_id: str,
        end_date: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Generate a monthly summary for a topic.

        Aggregates weekly summaries from the past month.
        """
        end_date = end_date or datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        # Get weekly summaries from the past month
        weekly_summaries = await self._get_summaries_in_period(
            topic_id,
            start_date,
            end_date,
            summary_type="weekly",
        )

        if not weekly_summaries:
            logger.info("No weekly summaries to consolidate", topic_id=topic_id)
            return None

        # Get topic info
        topic = await neo4j_client.get_node(topic_id, NodeLabels.TOPIC)
        if not topic:
            return None

        # Generate monthly summary
        summary_content = await self._generate_summary_with_llm(
            topic_title=topic.get("title", ""),
            topic_description=topic.get("description", ""),
            contexts=weekly_summaries,
            summary_type="monthly",
        )

        # Create summary node
        summary = await self._create_summary_node(
            topic_id=topic_id,
            title=f"Monthly Summary: {topic.get('title')} ({start_date.strftime('%Y-%m')})",
            content=summary_content,
            summary_type="monthly",
            period_start=start_date,
            period_end=end_date,
            source_context_ids=[s["id"] for s in weekly_summaries],
        )

        logger.info(
            "Generated monthly summary",
            topic_id=topic_id,
            summary_id=summary.get("id"),
            weekly_summary_count=len(weekly_summaries),
        )

        return summary

    async def _get_contexts_in_period(
        self,
        topic_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Get context nodes for a topic within a date range."""
        query = """
        MATCH (t:Topic {id: $topic_id})-[:HAS_CONTEXT]->(c:Context)
        WHERE c.created_at >= datetime($start_date)
          AND c.created_at <= datetime($end_date)
        RETURN c
        ORDER BY c.created_at
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(
                query,
                topic_id=topic_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            records = await result.data()
            return [dict(r["c"]) for r in records]

    async def _get_summaries_in_period(
        self,
        topic_id: str,
        start_date: datetime,
        end_date: datetime,
        summary_type: str,
    ) -> list[dict[str, Any]]:
        """Get summary nodes for a topic within a date range."""
        query = """
        MATCH (t:Topic {id: $topic_id})-[:HAS_SUMMARY]->(s:Summary)
        WHERE s.summary_type = $summary_type
          AND s.period_end >= datetime($start_date)
          AND s.period_end <= datetime($end_date)
        RETURN s
        ORDER BY s.period_end
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(
                query,
                topic_id=topic_id,
                summary_type=summary_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            records = await result.data()
            return [dict(r["s"]) for r in records]

    async def _generate_summary_with_llm(
        self,
        topic_title: str,
        topic_description: str | None,
        contexts: list[dict[str, Any]],
        summary_type: str,
    ) -> str:
        """Generate a summary using Claude."""
        # Format contexts for the prompt
        context_texts = []
        for i, ctx in enumerate(contexts, 1):
            source = ctx.get("source_type", "unknown")
            title = ctx.get("title", "Untitled")
            content = ctx.get("content", "")
            context_texts.append(f"{i}. [{source.upper()}] {title}\n{content}\n")

        contexts_str = "\n".join(context_texts)

        if summary_type == "weekly":
            prompt = f"""You are a knowledge management assistant. Summarize the following updates for the topic "{topic_title}".

Topic Description: {topic_description or 'N/A'}

Recent Updates:
{contexts_str}

Create a concise weekly summary that:
1. Highlights the most important developments
2. Notes any decisions made
3. Identifies key themes or patterns
4. Mentions any blockers or risks
5. Is written in clear, professional language

Summary:"""
        else:  # monthly
            prompt = f"""You are a knowledge management assistant. Create a monthly summary for the topic "{topic_title}" based on the following weekly summaries.

Topic Description: {topic_description or 'N/A'}

Weekly Summaries:
{contexts_str}

Create a comprehensive monthly summary that:
1. Synthesizes the key themes across weeks
2. Highlights major accomplishments
3. Notes significant decisions and their outcomes
4. Identifies trends and patterns
5. Provides strategic insights
6. Is written in clear, professional language

Monthly Summary:"""

        if self.llm_provider == "keywords_ai":
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        else:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

    async def _create_summary_node(
        self,
        topic_id: str,
        title: str,
        content: str,
        summary_type: str,
        period_start: datetime,
        period_end: datetime,
        source_context_ids: list[str],
    ) -> dict[str, Any]:
        """Create a summary node in the graph."""
        properties = {
            "id": str(uuid4()),
            "title": title,
            "content": content,
            "summary_type": summary_type,
            "topic_id": topic_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "source_context_ids": source_context_ids,
        }

        node = await neo4j_client.create_node(NodeLabels.SUMMARY, properties)

        # Create relationship to topic
        await neo4j_client.create_relationship(
            topic_id,
            node["id"],
            RelationshipTypes.HAS_SUMMARY,
        )

        return node

    async def consolidate_all_topics(
        self,
        summary_type: str = "weekly",
    ) -> dict[str, int]:
        """Run consolidation for all topics that need it.

        Returns counts of successful and failed consolidations.
        """
        # Get all topics
        query = """
        MATCH (t:Topic)
        RETURN t.id as topic_id, t.title as title
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(query)
            topics = await result.data()

        success_count = 0
        error_count = 0

        for topic in topics:
            try:
                if summary_type == "weekly":
                    summary = await self.generate_weekly_summary(topic["topic_id"])
                else:
                    summary = await self.generate_monthly_summary(topic["topic_id"])

                if summary:
                    success_count += 1
            except Exception as e:
                logger.error(
                    "Failed to generate summary",
                    topic_id=topic["topic_id"],
                    error=str(e),
                )
                error_count += 1

        return {"success": success_count, "errors": error_count}

    async def update_entity_importance(self) -> int:
        """Update importance scores for entities based on mention frequency.

        Returns the number of entities updated.
        """
        query = """
        MATCH (e:Entity)<-[:MENTIONS]-(c:Context)
        WITH e, count(c) as mention_count
        SET e.importance = CASE
            WHEN mention_count >= 10 THEN 1.0
            WHEN mention_count >= 5 THEN 0.8
            WHEN mention_count >= 3 THEN 0.6
            ELSE 0.4
        END,
        e.mention_count = mention_count,
        e.updated_at = datetime()
        RETURN count(e) as updated_count
        """

        async with neo4j_client.driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            count = record["updated_count"] if record else 0
            logger.info("Updated entity importance scores", count=count)
            return count


# Singleton instance
consolidation_service = ConsolidationService()
