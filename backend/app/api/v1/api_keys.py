import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.core.security import get_password_hash
from app.models.user import User
from app.models.api_key import APIKey

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_preview: str
    created_at: str | None = None
    last_used_at: str | None = None


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    return f"ck_{secrets.token_urlsafe(32)}"


async def verify_api_key(request: Request, db: AsyncSession):
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return None
    key_hash = hash_api_key(api_key_header)
    result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    if api_key:
        api_key.last_used_at = datetime.now(timezone.utc)
        await db.flush()
        return api_key
    return None


@router.get("/")
async def list_api_keys(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(APIKey).where(APIKey.business_id == current_user.business_id)
    )
    keys = result.scalars().all()
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_preview=k.key_hash[:8] + "...",
            created_at=str(k.created_at) if k.created_at else None,
            last_used_at=str(k.last_used_at) if k.last_used_at else None,
        )
        for k in keys
    ]


@router.post("/", status_code=201)
async def create_api_key(
    req: APIKeyCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    api_key = APIKey(
        business_id=current_user.business_id,
        key_hash=key_hash,
        name=req.name,
    )
    db.add(api_key)
    await db.flush()

    return {
        "id": api_key.id,
        "name": api_key.name,
        "api_key": raw_key,
        "key_preview": raw_key[:12] + "...",
        "created_at": str(api_key.created_at) if api_key.created_at else None,
    }


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.business_id == current_user.business_id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(api_key)
    await db.flush()
    return {"detail": "API key deleted"}
