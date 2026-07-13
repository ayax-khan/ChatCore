from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        if settings.VECTOR_DB_TYPE == "qdrant":
            from qdrant_client import QdrantClient
            self.client = QdrantClient(
                url=settings.QDRANT_URL or "http://localhost:6333",
                api_key=settings.QDRANT_API_KEY,
            )
        else:
            self.client = None

    def _collection_name(self, site_id: int) -> str:
        return f"{settings.QDRANT_COLLECTION_PREFIX}site_{site_id}"

    async def ensure_collection(self, site_id: int):
        if not self.client:
            return
        from qdrant_client.http.models import VectorParams, Distance
        name = self._collection_name(site_id)
        collections = self.client.get_collections().collections
        if not any(c.name == name for c in collections):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )

    async def search(
        self,
        site_id: int,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        if not self.client:
            return []
        name = self._collection_name(site_id)
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=str(value)),
                    ))
                search_filter = Filter(must=conditions) if conditions else None

            results = self.client.search(
                collection_name=name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=search_filter,
                with_payload=True,
            )
            return [
                {
                    "content": r.payload.get("content", ""),
                    "metadata": r.payload.get("metadata", {}),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Vector search failed: {e}")
            return []

    async def upsert_chunks(self, site_id: int, chunks: list[dict]):
        if not self.client:
            return
        try:
            from qdrant_client.http.models import PointStruct
            name = self._collection_name(site_id)
            await self.ensure_collection(site_id)
            points = []
            for i, chunk in enumerate(chunks):
                points.append(PointStruct(
                    id=hash(f"{site_id}_{i}_{chunk['content'][:100]}"),
                    vector=[0.0] * settings.EMBEDDING_DIMENSION,
                    payload={
                        "content": chunk.get("content", ""),
                        "metadata": chunk.get("metadata", {}),
                        "chunk_index": i,
                    },
                ))
            self.client.upsert(collection_name=name, points=points, wait=True)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to upsert chunks: {e}")

    async def delete_site_data(self, site_id: int):
        if not self.client:
            return
        try:
            self.client.delete_collection(self._collection_name(site_id))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to delete collection: {e}")
