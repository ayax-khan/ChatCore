from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.business import Business
from app.models.plan import Plan
from app.models.invoice import Invoice
from app.models.subscription import Subscription
from app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


class PaymentMethod(BaseModel):
    card_token: str
    last_four: str


class SubscriptionResponse(BaseModel):
    plan_id: int
    plan_name: str
    monthly_fee: float
    features: dict
    status: str
    usage: dict | None = None


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business).where(Business.id == current_user.business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    plan = None
    if business.plan_id:
        plan_result = await db.execute(select(Plan).where(Plan.id == business.plan_id))
        plan = plan_result.scalar_one_or_none()

    from app.services.cache_service import CacheService
    cache = CacheService()
    usage = await cache.get_usage_stats(current_user.business_id)

    return SubscriptionResponse(
        plan_id=business.plan_id or 1,
        plan_name=plan.name if plan else "Free",
        monthly_fee=plan.monthly_fee if plan else 0.0,
        features=plan.features if plan else {"sites": 1, "queries_per_month": 1000},
        status="active",
        usage=usage,
    )


@router.post("/upgrade")
async def upgrade_plan(
    plan_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = await db.execute(
        select(Business).where(Business.id == current_user.business_id)
    )
    business = result.scalar_one_or_none()
    if business:
        business.plan_id = plan_id
        await db.flush()

    return {"detail": f"Upgraded to {plan.name}", "plan_id": plan_id}


@router.get("/plans")
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).order_by(Plan.monthly_fee))
    plans = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "monthly_fee": p.monthly_fee,
            "features": p.features,
        }
        for p in plans
    ]


@router.post("/payment-method")
async def add_payment_method(
    req: PaymentMethod,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.analytics_event import AnalyticsEvent
    event = AnalyticsEvent(
        business_id=current_user.business_id,
        event_type="payment_method_added",
        properties={
            "last_four": req.last_four,
        },
    )
    db.add(event)
    await db.flush()
    return {"detail": "Payment method added"}


@router.get("/invoices")
async def list_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.business_id == current_user.business_id)
        .order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    return [
        {
            "id": inv.id,
            "amount": inv.amount,
            "status": inv.status,
            "stripe_invoice_id": inv.stripe_invoice_id,
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in invoices
    ]
