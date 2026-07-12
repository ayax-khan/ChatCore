from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.message import Message
from app.models.chat_session import ChatSession
from app.models.website import Website
from app.models.document_chunk import DocumentChunk
from app.models.analytics_event import AnalyticsEvent

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    period: str = Query("30d", regex="^(24h|7d|30d|90d)$"),
):
    now = datetime.now(timezone.utc)
    if period == "24h":
        since = now - timedelta(hours=24)
    elif period == "7d":
        since = now - timedelta(days=7)
    elif period == "90d":
        since = now - timedelta(days=90)
    else:
        since = now - timedelta(days=30)

    biz_id = current_user.business_id

    total_sessions = await db.execute(
        select(func.count(ChatSession.id)).where(
            ChatSession.business_id == biz_id,
            ChatSession.started_at >= since,
        )
    )

    total_messages = await db.execute(
        select(func.count(Message.id))
        .join(ChatSession)
        .where(
            ChatSession.business_id == biz_id,
            Message.timestamp >= since,
        )
    )

    dau_result = await db.execute(
        select(func.count(func.distinct(
            func.date_trunc("day", ChatSession.started_at)
        ))).where(
            ChatSession.business_id == biz_id,
            ChatSession.started_at >= since,
        )
    )

    active_days = dau_result.scalar() or 1
    total_sites = await db.execute(
        select(func.count(Website.id)).where(
            Website.business_id == biz_id
        )
    )

    total_chunks = await db.execute(
        select(func.count(DocumentChunk.id))
        .join(Website)
        .where(Website.business_id == biz_id)
    )

    feedback_result = await db.execute(
        select(
            func.count(AnalyticsEvent.id),
            func.avg(
                func.cast(
                    AnalyticsEvent.properties["rating"].as_text(), "integer"
                )
            ),
        ).where(
            AnalyticsEvent.business_id == biz_id,
            AnalyticsEvent.event_type == "feedback",
            AnalyticsEvent.created_at >= since,
        )
    )
    feedback_count, avg_rating = feedback_result.first() or (0, None)

    leads_result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.business_id == biz_id,
            AnalyticsEvent.event_type == "lead_captured",
            AnalyticsEvent.created_at >= since,
        )
    )
    leads_count = leads_result.scalar() or 0

    from app.services.cache_service import CacheService
    cache = CacheService()
    usage_data = await cache.get_usage_stats(biz_id)

    return {
        "total_sessions": total_sessions.scalar() or 0,
        "total_messages": total_messages.scalar() or 0,
        "daily_active_users": round((total_sessions.scalar() or 0) / max(active_days, 1)),
        "total_sites": total_sites.scalar() or 0,
        "total_chunks": total_chunks.scalar() or 0,
        "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
        "total_feedback": feedback_count or 0,
        "total_leads": leads_count,
        "ai_queries": usage_data.get("total_queries", 0),
        "ai_tokens": usage_data.get("total_tokens", 0),
        "ai_cost": round(usage_data.get("total_cost", 0) / 1000, 4),
        "period": period,
    }


@router.get("/errors")
async def get_errors(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
):
    result = await db.execute(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.business_id == current_user.business_id,
            AnalyticsEvent.event_type == "error",
        )
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "message": e.properties.get("message", ""),
            "source": e.properties.get("source", ""),
            "created_at": str(e.created_at) if e.created_at else None,
        }
        for e in events
    ]


@router.get("/top-questions")
async def get_top_questions(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, le=50),
):
    result = await db.execute(
        select(Message.text, func.count(Message.id).label("count"))
        .join(ChatSession)
        .where(
            ChatSession.business_id == current_user.business_id,
            Message.sender == "user",
        )
        .group_by(Message.text)
        .order_by(func.count(Message.id).desc())
        .limit(limit)
    )
    rows = result.all()
    return [{"question": row.text[:200], "count": row.count} for row in rows]


@router.get("/cost-breakdown")
async def get_cost_breakdown(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.cache_service import CacheService
    cache = CacheService()
    usage = await cache.get_usage_stats(current_user.business_id)

    result = await db.execute(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.business_id == current_user.business_id,
            AnalyticsEvent.event_type == "llm_call",
        )
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(100)
    )
    events = result.scalars().all()

    model_breakdown = {}
    for e in events:
        model = e.properties.get("model", "unknown")
        model_breakdown[model] = model_breakdown.get(model, 0) + 1

    return {
        "total_queries": usage.get("total_queries", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "total_cost": round(usage.get("total_cost", 0) / 1000, 4),
        "model_breakdown": model_breakdown,
    }


@router.get("/daily")
async def get_daily_metrics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, le=90),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    biz_id = current_user.business_id

    daily_data = await db.execute(
        select(
            func.date_trunc("day", ChatSession.started_at).label("day"),
            func.count(ChatSession.id).label("sessions"),
        )
        .where(
            ChatSession.business_id == biz_id,
            ChatSession.started_at >= since,
        )
        .group_by(func.date_trunc("day", ChatSession.started_at))
        .order_by(func.date_trunc("day", ChatSession.started_at))
    )

    return [
        {"date": str(row.day.date()), "sessions": row.sessions}
        for row in daily_data.all()
    ]
