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
                check_compatibility=False,  # Allow version mismatch between client and server
            )
        return self._client

    async def init_collections(self) -> None:
        """Initialize all Qdrant collections."""
        for collection_name in self.collections.values():
            try:
                # Try to get collection info to check if it exists
                # This works with both old and new Qdrant versions
                try:
                    await self.client.get_collection(collection_name)
                    logger.info("Collection exists", collection=collection_name)
                    continue  # Collection already exists
                except Exception:
                    pass  # Collection doesn't exist, create it

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
        tags: list[str] | None = None,
    ) -> str:
        """Store a text embedding in Qdrant.

        Args:
            collection: Collection name (knowledge, org_memory, etc.)
            text: Text to embed
            metadata: Additional metadata to store
            point_id: Optional custom point ID
            tags: Optional list of tags for cross-cutting filtering
        """
        collection_name = self.collections.get(collection)
        if not collection_name:
            raise ValueError(f"Unknown collection: {collection}")

        point_id = point_id or str(uuid4())

        try:
            # Generate embedding
            embedding = await self.generate_embedding(text)

            # Build payload with tags
            payload = {
                "text": text,
                **metadata,
            }

            # Add tags as a list field for filtering
            if tags:
                payload["tags"] = [t.lower().replace(" ", "-").replace("_", "-") for t in tags]

            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
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
                tags=tags,
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

            # Use HTTP API directly for compatibility with older Qdrant versions
            import httpx

            search_body: dict[str, Any] = {
                "vector": query_embedding,
                "limit": limit,
                "with_payload": True,
            }
            if score_threshold > 0:
                search_body["score_threshold"] = score_threshold
            if qdrant_filter:
                search_body["filter"] = {
                    "must": [
                        {"key": cond.key, "match": {"value": cond.match.value}}
                        for cond in qdrant_filter.must
                    ]
                }

            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{collection_name}/points/search",
                    json=search_body,
                    timeout=30.0,
                )
                data = response.json()

            if "result" not in data:
                logger.warning("Search returned no results", collection=collection, data=data)
                return []

            return [
                {
                    "score": hit.get("score", 0),
                    "payload": hit.get("payload", {}),
                    "id": hit.get("id"),
                }
                for hit in data["result"]
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
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search combining vector similarity, keyword matching, and tag filtering.

        This performs vector search and optionally:
        - Boosts results containing keywords
        - Filters/boosts results with matching tags
        """
        # Add tag filter if provided
        search_filters = filters.copy() if filters else {}

        # First, do vector search with higher limit
        vector_results = await self.search(
            collection=collection,
            query=query,
            limit=limit * 3,  # Get more results for post-filtering
            filters=search_filters,
        )

        if not keywords and not tags:
            return vector_results[:limit]

        # Process results
        keywords_lower = [k.lower() for k in keywords] if keywords else []
        tags_normalized = [t.lower().replace(" ", "-").replace("_", "-") for t in tags] if tags else []

        for result in vector_results:
            payload = result.get("payload", {})
            text = payload.get("text", "").lower()
            result_tags = payload.get("tags", [])

            # Keyword boost (up to 20%)
            if keywords_lower:
                keyword_matches = sum(1 for k in keywords_lower if k in text)
                keyword_boost = min(0.2, keyword_matches * 0.05)
            else:
                keyword_boost = 0

            # Tag boost (up to 30% for matching tags)
            if tags_normalized:
                tag_matches = sum(1 for t in tags_normalized if t in result_tags)
                tag_boost = min(0.3, tag_matches * 0.1)
            else:
                tag_boost = 0

            result["score"] = result["score"] * (1 + keyword_boost + tag_boost)
            result["keyword_matches"] = keyword_matches if keywords_lower else 0
            result["tag_matches"] = tag_matches if tags_normalized else 0

        # Re-sort by boosted score
        vector_results.sort(key=lambda x: x["score"], reverse=True)
        return vector_results[:limit]

    async def search_by_tags(
        self,
        collection: str,
        tags: list[str],
        query: str | None = None,
        limit: int = 10,
        require_all_tags: bool = False,
    ) -> list[dict[str, Any]]:
        """Search primarily by tags, optionally combined with semantic search.

        This allows bypassing hierarchy-based navigation entirely.
        """
        tags_normalized = [t.lower().replace(" ", "-").replace("_", "-") for t in tags]
        collection_name = self.collections.get(collection)
        if not collection_name:
            raise ValueError(f"Unknown collection: {collection}")

        try:
            import httpx

            # Build the search body
            search_body: dict[str, Any] = {
                "limit": limit * 2 if query else limit,
                "with_payload": True,
            }

            # If we have a query, do vector search with tag filter
            if query:
                query_embedding = await self.generate_embedding(query)
                search_body["vector"] = query_embedding

            # Build tag filter
            if require_all_tags:
                # Must have ALL tags
                tag_conditions = [
                    {"key": "tags", "match": {"any": [tag]}}
                    for tag in tags_normalized
                ]
                search_body["filter"] = {"must": tag_conditions}
            else:
                # Must have ANY of the tags
                search_body["filter"] = {
                    "must": [{"key": "tags", "match": {"any": tags_normalized}}]
                }

            async with httpx.AsyncClient() as http_client:
                if query:
                    # Vector search with filter
                    endpoint = f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{collection_name}/points/search"
                else:
                    # Scroll with filter (no vector)
                    endpoint = f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{collection_name}/points/scroll"
                    search_body["limit"] = limit

                response = await http_client.post(endpoint, json=search_body, timeout=30.0)
                data = response.json()

            results_key = "result" if query else "result"
            if results_key not in data:
                return []

            results = data[results_key]
            if isinstance(results, dict) and "points" in results:
                results = results["points"]

            return [
                {
                    "score": hit.get("score", 1.0),
                    "payload": hit.get("payload", {}),
                    "id": hit.get("id"),
                }
                for hit in results
            ][:limit]

        except Exception as e:
            logger.warning("Tag search failed", collection=collection, error=str(e))
            return []

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

    async def embed_and_store(
        self,
        documents: list[dict[str, Any]],
    ) -> list[str]:
        """Embed and store multiple documents.

        Each document should have:
        - text: The text to embed
        - collection: Which collection to store in ('knowledge', 'org_memory', etc.)
        - Additional metadata fields

        Returns list of stored point IDs.
        """
        stored_ids = []

        for doc in documents:
            text = doc.get("text", "")
            collection = doc.get("collection", "knowledge")

            if not text:
                continue

            # Build metadata (exclude text and collection)
            metadata = {k: v for k, v in doc.items() if k not in ("text", "collection")}

            try:
                point_id = await self.store_embedding(
                    collection=collection,
                    text=text,
                    metadata=metadata,
                )
                stored_ids.append(point_id)
            except Exception as e:
                logger.warning(
                    "Failed to embed document",
                    title=doc.get("title", "untitled"),
                    error=str(e),
                )

        return stored_ids

    async def store_chat_embedding(
        self,
        department: str,
        topic: str,
        chat_content: str,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a chat interaction embedding for the textbook architecture.

        This is used to build the department-organized knowledge base
        where chats are embedded and can be retrieved by department/topic.
        """
        text_to_embed = summary if summary else chat_content

        embedding_metadata = {
            "department": department,
            "topic": topic,
            "content_type": "chat_summary" if summary else "chat",
            "original_content": chat_content[:500] if len(chat_content) > 500 else chat_content,
            **(metadata or {}),
        }

        return await self.store_embedding(
            collection="knowledge",
            text=text_to_embed,
            metadata=embedding_metadata,
        )


# Singleton instance
embedder = EmbeddingService()
