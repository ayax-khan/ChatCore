import asyncio
import json
import logging
import time
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_metadata: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str, metadata: dict | None = None):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.connection_metadata[session_id] = metadata or {}
        logger.info(f"WebSocket connected: session_id={session_id}")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        self.connection_metadata.pop(session_id, None)
        logger.info(f"WebSocket disconnected: session_id={session_id}")

    async def send_message(self, session_id: str, message: dict):
        websocket = self.active_connections.get(session_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)

    async def stream_token(self, session_id: str, token: str):
        await self.send_message(session_id, {
            "type": "token",
            "content": token,
        })

    async def stream_sources(self, session_id: str, sources: list[dict]):
        await self.send_message(session_id, {
            "type": "sources",
            "sources": sources,
        })

    async def stream_confidence(self, session_id: str, confidence: float):
        await self.send_message(session_id, {
            "type": "confidence",
            "confidence": confidence,
        })

    async def stream_done(self, session_id: str, answer: str):
        await self.send_message(session_id, {
            "type": "done",
            "answer": answer,
        })

    async def stream_error(self, session_id: str, error: str):
        await self.send_message(session_id, {
            "type": "error",
            "content": error,
        })

    async def broadcast(self, message: dict):
        disconnected = []
        for session_id, ws in self.active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(session_id)
        for sid in disconnected:
            self.disconnect(sid)


manager = ConnectionManager()


class ChatStreamService:
    def __init__(self):
        self.manager = manager

    async def stream_answer(
        self,
        session_id: str,
        site_id: int,
        question: str,
        conversation_history: list[dict] | None = None,
    ):
        from app.services.rag import RAGService
        rag = RAGService()

        try:
            chunks = await rag.retrieve_chunks(site_id, question)
            if not chunks:
                await self.manager.stream_token(session_id, "I cannot answer based on the provided information.")
                await self.manager.stream_confidence(session_id, 0.0)
                await self.manager.stream_sources(session_id, [])
                await self.manager.stream_done(session_id, "I cannot answer based on the provided information.")
                return

            context = "\n\n".join(
                f"[{i+1}] {ch['content']}" for i, ch in enumerate(chunks)
            )
            sources = [
                {"url": ch.get("metadata", {}).get("url", ""), "snippet": ch["content"][:200]}
                for ch in chunks
            ]

            await self.manager.stream_sources(session_id, sources)

            prompt = rag._build_prompt(question, context, conversation_history)

            full_answer = ""
            from app.services.llm_service import LLMService
            llm = LLMService()
            async for token in llm.stream_generate(prompt):
                full_answer += token
                await self.manager.stream_token(session_id, token)
                await asyncio.sleep(0.01)

            confidence = rag._calculate_confidence(chunks)
            await self.manager.stream_confidence(session_id, confidence)
            await self.manager.stream_done(session_id, full_answer)

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Stream error: {e}", exc_info=True)
            await self.manager.stream_error(session_id, str(e))
