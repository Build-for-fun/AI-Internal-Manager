"""Embedding generation and vector storage with Qdrant."""

from typing import Any
from uuid import uuid4

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating embeddings and storing them in Qdrant."""

    def __init__(self):
        self._client: AsyncQdrantClient | None = None
        self._embedding_client = None

        # Collection names
        self.collections = {
            "org_memory": f"{settings.qdrant_collection_prefix}_org_memory",
            "user_memory": f"{settings.qdrant_collection_prefix}_user_memory",
            "team_memory": f"{settings.qdrant_collection_prefix}_team_memory",
            "knowledge": f"{settings.qdrant_collection_prefix}_knowledge",
        }

    @property
    def client(self) -> AsyncQdrantClient:
        """Get the Qdrant client."""
        if not self._client:
            self._client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )
        return self._client

    async def init_collections(self) -> None:
        """Initialize all Qdrant collections."""
        for collection_name in self.collections.values():
            try:
                # Check if collection exists
                exists = await self.client.collection_exists(collection_name)
                if not exists:
                    await self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=settings.embedding_dimension,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info("Created collection", collection=collection_name)
            except Exception as e:
                logger.error("Failed to create collection", collection=collection_name, error=str(e))

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using configured provider."""
        try:
            if settings.embedding_provider == "voyage":
                return await self._generate_voyage_embedding(text)
            else:
                return await self._generate_openai_embedding(text)
        except Exception as e:
            logger.warning("Embedding generation failed, using dummy", error=str(e))
            # Return random unit vector or zero vector
            return [0.0] * settings.embedding_dimension

    async def _generate_voyage_embedding(self, text: str) -> list[float]:
        """Generate embedding using Voyage AI."""
        import voyageai
        
        api_key = settings.voyage_api_key.get_secret_value()
        if not api_key or api_key == "placeholder":
             # Return dummy vector if no key
            return [0.0] * settings.embedding_dimension

        if not self._embedding_client:
            self._embedding_client = voyageai.AsyncClient(
                api_key=api_key
            )

        result = await self._embedding_client.embed(
            texts=[text],
            model=settings.voyage_model,
            input_type="document",
        )
        return result.embeddings[0]

    async def _generate_openai_embedding(self, text: str) -> list[float]:
        """Generate embedding using OpenAI."""
        from openai import AsyncOpenAI
        
        api_key = settings.openai_api_key.get_secret_value()
        if not api_key or api_key == "placeholder":
            return [0.0] * settings.embedding_dimension

        if not self._embedding_client:
            self._embedding_client = AsyncOpenAI(
                api_key=api_key
            )

        response = await self._embedding_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def store_embedding(
        self,
        collection: str,
        text: str,
        metadata: dict[str, Any],
        point_id: str | None = None,
    ) -> str:
        """Store a text embedding in Qdrant."""
        collection_name = self.collections.get(collection)
        if not collection_name:
            raise ValueError(f"Unknown collection: {collection}")

        point_id = point_id or str(uuid4())

        try:
            # Generate embedding
            embedding = await self.generate_embedding(text)

            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": text,
                    **metadata,
                },
            )

            # Upsert to collection
            await self.client.upsert(
                collection_name=collection_name,
                points=[point],
            )

            logger.debug(
                "Stored embedding",
                collection=collection,
                point_id=point_id,
            )
        except Exception as e:
            logger.warning("Failed to store embedding", collection=collection, error=str(e))

        return point_id

    async def search(
        self,
        collection: str,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search for similar embeddings in a collection."""
        collection_name = self.collections.get(collection)
        if not collection_name:
            raise ValueError(f"Unknown collection: {collection}")

        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)

            # Build filter if provided
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                qdrant_filter = Filter(must=conditions)

            # Search
            results = await self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=qdrant_filter,
                score_threshold=score_threshold,
            )

            return [
                {
                    "score": hit.score,
                    "payload": hit.payload,
                    "id": hit.id,
                }
                for hit in results
            ]
        except Exception as e:
            logger.warning("Search failed", collection=collection, error=str(e))
            return []

    async def hybrid_search(
        self,
        collection: str,
        query: str,
        keywords: list[str] | None = None,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search combining vector similarity and keyword matching.

        This performs vector search and optionally boosts results containing keywords.
        """
        # First, do vector search with higher limit
        vector_results = await self.search(
            collection=collection,
            query=query,
            limit=limit * 2,
            filters=filters,
        )

        if not keywords:
            return vector_results[:limit]

        # Boost scores for results containing keywords
        keywords_lower = [k.lower() for k in keywords]
        for result in vector_results:
            text = result.get("text", "").lower()
            keyword_matches = sum(1 for k in keywords_lower if k in text)
            # Boost score by up to 20% based on keyword matches
            boost = min(0.2, keyword_matches * 0.05)
            result["score"] = result["score"] * (1 + boost)

        # Re-sort by boosted score
        vector_results.sort(key=lambda x: x["score"], reverse=True)
        return vector_results[:limit]

    async def delete_embedding(self, collection: str, point_id: str) -> bool:
        """Delete an embedding from a collection."""
        collection_name = self.collections.get(collection)
        if not collection_name:
            raise ValueError(f"Unknown collection: {collection}")

        await self.client.delete(
            collection_name=collection_name,
            points_selector=[point_id],
        )
        return True

    async def delete_by_filter(
        self,
        collection: str,
        filters: dict[str, Any],
    ) -> int:
        """Delete embeddings matching filters.

        Returns the number of points deleted.
        """
        collection_name = self.collections.get(collection)
        if not collection_name:
            raise ValueError(f"Unknown collection: {collection}")

        # Build filter
        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )
        qdrant_filter = Filter(must=conditions)

        # Get count before deletion
        count_before = await self.client.count(
            collection_name=collection_name,
            count_filter=qdrant_filter,
        )

        # Delete
        await self.client.delete(
            collection_name=collection_name,
            points_selector=qdrant_filter,
        )

        return count_before.count


# Singleton instance
embedder = EmbeddingService()
