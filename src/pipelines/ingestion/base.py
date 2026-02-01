"""Base class for ingestion pipelines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class IngestionResult:
    """Result of an ingestion run."""

    source: str
    started_at: datetime
    completed_at: datetime | None = None
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if not self.completed_at:
            return 0
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.items_processed == 0:
            return 1.0
        return 1 - (len(self.errors) / self.items_processed)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "items_processed": self.items_processed,
            "items_created": self.items_created,
            "items_updated": self.items_updated,
            "items_skipped": self.items_skipped,
            "error_count": len(self.errors),
            "success_rate": self.success_rate,
        }


class BaseIngestionPipeline(ABC):
    """Base class for data ingestion pipelines.

    Each pipeline:
    1. Fetches data from an external source
    2. Normalizes it to our schema
    3. Stores in the knowledge graph
    4. Generates embeddings for vector search
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    async def fetch_data(self, **kwargs) -> list[Any]:
        """Fetch data from the external source."""
        pass

    @abstractmethod
    async def normalize(self, raw_data: Any) -> dict[str, Any]:
        """Normalize raw data to our schema."""
        pass

    @abstractmethod
    async def store(self, normalized_data: dict[str, Any]) -> str:
        """Store normalized data in the knowledge graph.

        Returns the node ID of the created/updated node.
        """
        pass

    async def run(self, **kwargs) -> IngestionResult:
        """Run the complete ingestion pipeline."""
        result = IngestionResult(
            source=self.source_name,
            started_at=datetime.utcnow(),
        )

        logger.info("Starting ingestion", source=self.source_name)

        try:
            # Fetch data
            raw_items = await self.fetch_data(**kwargs)
            result.items_processed = len(raw_items)

            # Process each item
            for item in raw_items:
                try:
                    # Normalize
                    normalized = await self.normalize(item)
                    if not normalized:
                        result.items_skipped += 1
                        continue

                    # Store
                    node_id = await self.store(normalized)

                    # Generate embedding
                    await self._generate_embedding(node_id, normalized)

                    result.items_created += 1

                except Exception as e:
                    error_msg = f"Failed to process item: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg, source=self.source_name)

        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg, source=self.source_name)

        result.completed_at = datetime.utcnow()

        logger.info(
            "Ingestion completed",
            source=self.source_name,
            processed=result.items_processed,
            created=result.items_created,
            errors=len(result.errors),
            duration=result.duration_seconds,
        )

        return result

    async def _generate_embedding(
        self,
        node_id: str,
        data: dict[str, Any],
    ) -> None:
        """Generate and store embedding for the data."""
        from src.knowledge.indexing.embedder import embedder

        # Build text for embedding
        title = data.get("title", "")
        content = data.get("content", "")
        text = f"{title}\n\n{content}" if title else content

        if not text:
            return

        await embedder.store_embedding(
            collection="knowledge",
            text=text,
            metadata={
                "node_id": node_id,
                "source_type": self.source_name,
                **{k: v for k, v in data.items() if k not in ["title", "content"]},
            },
            point_id=node_id,
        )
