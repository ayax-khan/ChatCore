import logging
import re
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db.session import async_session_factory
from app.models.document_chunk import DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)


class SparseSearchService:
    def __init__(self):
        self.min_score = 0.1

    async def search(
        self,
        site_id: int,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        async with async_session_factory() as db:
            stmt = select(DocumentChunk).where(
                DocumentChunk.site_id == site_id
            )

            metadata_filters = filters or {}
            if metadata_filters:
                for key, value in metadata_filters.items():
                    stmt = stmt.where(
                        DocumentChunk.metadata[key].as_string() == str(value)
                    )

            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append(DocumentChunk.content.ilike(f"%{kw}%"))
            if keyword_conditions:
                stmt = stmt.where(or_(*keyword_conditions))

            stmt = stmt.limit(top_k * 3)
            result = await db.execute(stmt)
            chunks = result.scalars().all()

        scored = []
        for chunk in chunks:
            score = self._compute_relevance(chunk.content, query, keywords)
            if score >= self.min_score:
                scored.append({
                    "content": chunk.content,
                    "metadata": chunk.metadata or {},
                    "score": score,
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _extract_keywords(self, query: str) -> list[str]:
        cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
        words = cleaned.split()
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "because",
            "and", "but", "or", "if", "while", "about", "up", "what",
            "which", "who", "whom", "this", "that", "these", "those", "it",
            "its", "i", "me", "my", "we", "our", "you", "your", "he", "she",
            "they", "them", "their", "his", "her", "its", "him",
        }
        return [w for w in words if len(w) > 2 and w not in stop_words][:10]

    def _compute_relevance(self, content: str, query: str, keywords: list[str]) -> float:
        content_lower = content.lower()
        query_lower = query.lower()

        keyword_matches = sum(1 for kw in keywords if kw in content_lower)
        if not keywords:
            return 0.0
        keyword_score = keyword_matches / len(keywords)

        phrase_matches = 0
        query_words = query_lower.split()
        for i in range(len(query_words) - 1):
            phrase = " ".join(query_words[i:i+2])
            if phrase in content_lower:
                phrase_matches += 1
        phrase_score = phrase_matches / max(len(query_words) - 1, 1) * 0.3

        exact_match = 1.0 if query_lower in content_lower else 0.0
        exact_boost = exact_match * 0.4

        total = min(1.0, keyword_score * 0.5 + phrase_score + exact_boost)
        return round(total, 4)


class HybridSearchService:
    def __init__(self):
        self.dense_weight = 0.6
        self.sparse_weight = 0.4

    async def search(
        self,
        site_id: int,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        from app.services.vector_store import VectorStoreService
        from app.services.sparse_search import SparseSearchService

        vs = VectorStoreService()
        ss = SparseSearchService()

        dense_task = vs.search(site_id, query_embedding, top_k=top_k, filters=filters)
        sparse_task = ss.search(site_id, query, top_k=top_k, filters=filters)

        import asyncio
        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

        combined = {}
        for i, dr in enumerate(dense_results):
            combined[i] = {
                "content": dr["content"],
                "metadata": dr.get("metadata", {}),
                "dense_score": dr.get("score", 0),
                "sparse_score": 0.0,
                "score": dr.get("score", 0) * self.dense_weight,
            }

        for sr in sparse_results:
            matched = False
            for key, item in combined.items():
                if item["content"] == sr["content"]:
                    item["sparse_score"] = sr.get("score", 0)
                    item["score"] = item["dense_score"] * self.dense_weight + sr.get("score", 0) * self.sparse_weight
                    matched = True
                    break
            if not matched:
                new_key = len(combined)
                combined[new_key] = {
                    "content": sr["content"],
                    "metadata": sr.get("metadata", {}),
                    "dense_score": 0.0,
                    "sparse_score": sr.get("score", 0),
                    "score": sr.get("score", 0) * self.sparse_weight,
                }

        results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        return results[:top_k]
