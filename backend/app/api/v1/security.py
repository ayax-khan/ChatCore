import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.core.config import settings
from app.core.security import create_access_token, decode_token, verify_password, get_password_hash
from app.models.user import User
from app.models.analytics_event import AnalyticsEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


class OAuthLoginRequest(BaseModel):
    provider: str
    code: str
    redirect_uri: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class GDPRExportResponse(BaseModel):
    data: dict
    format: str = "json"


@router.post("/oauth/login")
async def oauth_login(
    req: OAuthLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    if req.provider not in ("google", "microsoft", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {req.provider}")

    try:
        import httpx
        if req.provider == "google":
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": req.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": req.redirect_uri,
                "grant_type": "authorization_code",
            }
        elif req.provider == "microsoft":
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            data = {
                "code": req.code,
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "redirect_uri": req.redirect_uri,
                "grant_type": "authorization_code",
            }
        elif req.provider == "github":
            token_url = "https://github.com/login/oauth/access_token"
            data = {
                "code": req.code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": req.redirect_uri,
            }

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(token_url, data=data, headers={"Accept": "application/json"})
            token_data = token_resp.json()
            if "access_token" not in token_data:
                raise HTTPException(status_code=401, detail="OAuth token exchange failed")

            access_token_oauth = token_data["access_token"]
            if req.provider == "google":
                userinfo = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token_oauth}"}
                )
            elif req.provider == "microsoft":
                userinfo = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token_oauth}"}
                )
            elif req.provider == "github":
                userinfo = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token_oauth}"}
                )

            user_data = userinfo.json()
            email = user_data.get("email") or user_data.get("userPrincipalName", "")
            name = user_data.get("name", "")
            if not email:
                raise HTTPException(status_code=401, detail="Could not get email from OAuth provider")

            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                from app.models.business import Business
                business = Business(name=name or email.split("@")[0])
                db.add(business)
                await db.flush()
                user = User(
                    business_id=business.id,
                    email=email,
                    hashed_password=get_password_hash("oauth_" + access_token_oauth[-20:]),
                    role="admin",
                )
                db.add(user)
                await db.flush()

            jwt_token = create_access_token({
                "sub": str(user.id),
                "role": user.role,
                "business_id": user.business_id,
            })

            event = AnalyticsEvent(
                business_id=user.business_id,
                event_type="oauth_login",
                properties={"provider": req.provider, "user_id": user.id},
            )
            db.add(event)
            await db.flush()

            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": user.id, "email": user.email, "name": name},
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth login failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="OAuth authentication failed")


@router.post("/change-password")
async def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    current_user.hashed_password = get_password_hash(req.new_password)
    await db.flush()

    event = AnalyticsEvent(
        business_id=current_user.business_id,
        event_type="password_changed",
        properties={"user_id": current_user.id},
    )
    db.add(event)
    await db.flush()

    return {"detail": "Password changed successfully"}


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.business_id == current_user.business_id,
            AnalyticsEvent.event_type == "login",
        )
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(50)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "timestamp": str(e.created_at) if e.created_at else None,
            "ip": e.properties.get("ip", ""),
            "user_agent": e.properties.get("user_agent", ""),
        }
        for e in events
    ]


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = AnalyticsEvent(
        business_id=current_user.business_id,
        event_type="logout",
        properties={"user_id": current_user.id},
    )
    db.add(event)
    await db.flush()
    return {"detail": "Logged out successfully"}


@router.get("/gdpr/export")
async def gdpr_export(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.chat_session import ChatSession
    from app.models.message import Message
    from app.models.business import Business
    from app.models.website import Website

    business = await db.get(Business, current_user.business_id)
    user_result = await db.execute(
        select(User).where(User.business_id == current_user.business_id)
    )
    users = user_result.scalars().all()
    sites_result = await db.execute(
        select(Website).where(Website.business_id == current_user.business_id)
    )
    sites = sites_result.scalars().all()

    return {
        "user": {
            "email": current_user.email,
            "role": current_user.role,
            "created_at": str(current_user.created_at) if current_user.created_at else None,
        },
        "business": {
            "name": business.name if business else "N/A",
            "created_at": str(business.created_at) if business and business.created_at else None,
        },
        "team_members": [
            {"email": u.email, "role": u.role} for u in users
        ],
        "websites": [
            {"url": s.url, "name": s.name, "status": s.status} for s in sites
        ],
        "export_date": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/gdpr/delete")
async def gdpr_delete(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.business import Business
    business = await db.get(Business, current_user.business_id)
    if business:
        await db.delete(business)
    else:
        await db.delete(current_user)
    await db.flush()
    return {"detail": "All personal data has been deleted"}


@router.get("/audit-logs")
async def audit_logs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    result = await db.execute(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.business_id == current_user.business_id,
            AnalyticsEvent.event_type.in_(["login", "logout", "password_changed", "site_added", "site_deleted", "crawl", "user_invited", "user_deleted"]),
        )
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "type": e.event_type,
            "details": e.properties,
            "timestamp": str(e.created_at) if e.created_at else None,
        }
        for e in events
    ]
