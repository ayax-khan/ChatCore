import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.chat_session import ChatSession
from app.models.message import Message
from app.models.source import Source
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class ChatPersistenceService:
    async def get_or_create_session(
        self,
        db: AsyncSession,
        business_id: int,
        session_id: str,
        user_id: int | None = None,
    ) -> ChatSession:
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            session = ChatSession(
                business_id=business_id,
                session_id=session_id,
                user_id=user_id,
                started_at=datetime.now(timezone.utc),
            )
            db.add(session)
            await db.flush()
        return session

    async def save_message(
        self,
        db: AsyncSession,
        chat_id: int,
        sender: str,
        text: str,
    ) -> Message:
        msg = Message(
            chat_id=chat_id,
            sender=sender,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(msg)
        await db.flush()
        return msg

    async def save_sources(
        self,
        db: AsyncSession,
        message_id: int,
        sources_data: list[dict],
    ):
        for src in sources_data:
            if isinstance(src, dict):
                source = Source(
                    message_id=message_id,
                    snippet=src.get("snippet", "")[:500],
                    url=src.get("url", ""),
                    score=src.get("score", 0),
                )
                db.add(source)
        await db.flush()

    async def get_session_history(
        self,
        db: AsyncSession,
        session_id: str,
        max_messages: int = 20,
    ) -> list[dict]:
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return []
        msgs_result = await db.execute(
            select(Message)
            .where(Message.chat_id == session.id)
            .order_by(Message.timestamp.desc())
            .limit(max_messages)
        )
        messages = msgs_result.scalars().all()
        messages.reverse()
        return [
            {"sender": m.sender, "text": m.text}
            for m in messages
        ]

    async def close_session(self, db: AsyncSession, session_id: str):
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.ended_at = datetime.now(timezone.utc)
            await db.flush()
