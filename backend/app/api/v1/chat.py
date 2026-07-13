from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.services.rag import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    site_id: int
    session_id: str = ""
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float


@router.post("/")
async def chat(
    req: ChatRequest,
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.rag import RAGService
    from app.models.chat_session import ChatSession
    from app.models.message import Message
    from sqlalchemy import select
    import uuid

    if not req.session_id:
        req.session_id = str(uuid.uuid4())

    rag = RAGService()
    answer, sources, confidence = await rag.answer_question(
        site_id=req.site_id,
        question=req.question,
    )

    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == req.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        session = ChatSession(
            business_id=current_user.business_id if current_user else 1,
            session_id=req.session_id,
        )
        db.add(session)
        await db.flush()

    user_msg = Message(chat_id=session.id, sender="user", text=req.question)
    bot_msg = Message(chat_id=session.id, sender="ai", text=answer)
    db.add(user_msg)
    db.add(bot_msg)
    await db.flush()

    return {"answer": answer, "sources": sources, "confidence": confidence, "session_id": req.session_id}
