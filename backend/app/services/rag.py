import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.chat_model = settings.OPENAI_CHAT_MODEL
        self.top_k = settings.TOP_K_RETRIEVAL

    async def embed_text(self, text: str) -> list[float]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            resp = await client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return resp.data[0].embedding
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Embedding failed: {e}")
            return [0.0] * settings.EMBEDDING_DIMENSION

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            resp = await client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            embeddings = [item.embedding for item in resp.data]
            while len(embeddings) < len(texts):
                embeddings.append([0.0] * settings.EMBEDDING_DIMENSION)
            return embeddings
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Batch embedding failed: {e}")
            return [[0.0] * settings.EMBEDDING_DIMENSION for _ in texts]

    async def retrieve_chunks(self, site_id: int, query: str, top_k: int | None = None) -> list[dict]:
        from app.services.vector_store import VectorStoreService
        k = top_k or self.top_k
        vs = VectorStoreService()
        query_embedding = await self.embed_text(query)
        results = await vs.search(site_id, query_embedding, top_k=k)

        if not results:
            from app.services.sparse_search import SparseSearchService
            sparse = SparseSearchService()
            sparse_results = await sparse.search(site_id, query, top_k=k)
            if sparse_results:
                for sr in sparse_results:
                    sr["score"] = sr.get("score", 0.5) * 0.8
                return sparse_results

        return results

    def _build_prompt(
        self,
        question: str,
        context: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-6:]:
                sender = "User" if msg.get("sender") == "user" else "Assistant"
                history_parts.append(f"{sender}: {msg.get('text', '')}")
            history_text = "\n".join(history_parts) + "\n\n"

        sanitized_question = question.replace("{", "{{").replace("}", "}}")

        prompt = f"""You are a helpful assistant for a website knowledge base. Answer the question using ONLY the provided source excerpts. Follow these rules strictly:

1. Base your answer ONLY on the sources listed below
2. If the sources don't contain enough information, say "I cannot answer based on the provided information."
3. Cite your sources using [1], [2], etc. at the relevant parts of your answer
4. Do NOT make up facts or use external knowledge
5. If asked about things outside the sources, politely decline
6. Format your answer in clear paragraphs. Use markdown for lists or code if needed.
7. Keep your answer concise but complete

{history_text}Sources:
{context}

Question: {sanitized_question}

Answer:"""
        return prompt

    def _calculate_confidence(self, chunks: list[dict]) -> float:
        if not chunks:
            return 0.0
        scores = [ch.get("score", 0.5) for ch in chunks]
        avg_score = sum(scores) / len(scores)
        if avg_score > 0.8:
            return round(min(0.98, avg_score), 2)
        elif avg_score > 0.6:
            return round(avg_score, 2)
        elif avg_score > 0.3:
            return round(max(0.2, avg_score), 2)
        else:
            return round(max(0.05, avg_score), 2)

    async def answer_question(self, site_id: int, question: str) -> tuple[str, list[dict], float]:
        chunks = await self.retrieve_chunks(site_id, question)
        if not chunks:
            return "I cannot answer based on the provided information.", [], 0.0

        context = "\n\n".join(
            f"[{i+1}] {ch['content']}" for i, ch in enumerate(chunks)
        )
        sources = [
            {"url": ch.get("metadata", {}).get("url", ""), "snippet": ch["content"][:200]}
            for ch in chunks
        ]

        prompt = self._build_prompt(question, context)

        try:
            from app.services.llm_service import LLMService
            llm = LLMService()
            answer = await llm.generate(prompt)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"LLM call failed: {e}")
            answer = "I'm sorry, I encountered an error processing your request."

        confidence = self._calculate_confidence(chunks)
        return answer, sources, confidence

    async def generate_suggested_questions(self, site_id: int, count: int = 3) -> list[str]:
        try:
            from app.services.vector_store import VectorStoreService
            vs = VectorStoreService()
            random_embedding = [0.0] * settings.EMBEDDING_DIMENSION
            random_embedding[0] = 1.0
            chunks = await vs.search(site_id, random_embedding, top_k=5)
            if not chunks:
                return ["What services do you offer?", "What are your hours?", "How can I contact you?"]

            topics = [ch["content"][:100] for ch in chunks]
            context = "\n".join(f"- {t}" for t in topics)

            prompt = f"""Based on these website content snippets, generate {count} natural questions that visitors might ask:

{context}

Return only the questions, one per line, numbered 1-{count}."""

            from app.services.llm_service import LLMService
            llm = LLMService()
            result = await llm.generate(prompt)
            questions = []
            for line in result.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    clean = line.split(". ", 1)[-1] if ". " in line else line
                    clean = clean.lstrip("- ")
                    questions.append(clean)
            return questions[:count]
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate questions: {e}")
            return ["What services do you offer?", "What are your hours?", "How can I contact you?"]
