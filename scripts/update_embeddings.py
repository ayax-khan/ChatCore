"""
Script to update embeddings for all document chunks.
Run: python scripts/update_embeddings.py
"""
import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.document_chunk import DocumentChunk
from app.services.rag import RAGService


async def main():
    rag = RAGService()
    async with async_session_factory() as session:
        result = await session.execute(select(DocumentChunk))
        chunks = result.scalars().all()
        for chunk in chunks:
            embedding = await rag.embed_text(chunk.content)
            print(f"Updated chunk {chunk.id}: {len(embedding)} dimensions")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
