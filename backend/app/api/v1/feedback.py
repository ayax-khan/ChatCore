from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.analytics_event import AnalyticsEvent

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    session_id: str
    message_id: int | None = None
    rating: int
    comment: str | None = None


class LeadCreate(BaseModel):
    site_id: int
    session_id: str
    email: str
    name: str | None = None
    question: str | None = None
    consent: bool = False


@router.post("/")
async def submit_feedback(
    req: FeedbackCreate,
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    event = AnalyticsEvent(
        business_id=getattr(current_user, "business_id", 1),
        event_type="feedback",
        properties={
            "session_id": req.session_id,
            "message_id": req.message_id,
            "rating": req.rating,
            "comment": req.comment,
        },
    )
    db.add(event)
    await db.flush()

    return {"detail": "Feedback received", "rating": req.rating}


@router.post("/lead", status_code=201)
async def capture_lead(
    req: LeadCreate,
    db: AsyncSession = Depends(get_db),
):
    if not req.consent:
        raise HTTPException(status_code=400, detail="User consent required")

    import re
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    event = AnalyticsEvent(
        business_id=1,
        event_type="lead_captured",
        properties={
            "site_id": req.site_id,
            "session_id": req.session_id,
            "email": req.email,
            "name": req.name,
            "question": req.question,
            "consent": req.consent,
        },
    )
    db.add(event)
    await db.flush()

    return {"detail": "Lead captured successfully", "email": req.email}


@router.get("/suggested-questions")
async def get_suggested_questions(
    site_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.services.rag import RAGService
    rag = RAGService()
    questions = await rag.generate_suggested_questions(site_id)
    return {"questions": questions}
