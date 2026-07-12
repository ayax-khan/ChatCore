from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.core.security import get_password_hash
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "viewer"


class UserUpdate(BaseModel):
    role: str | None = None
    active: bool | None = None


@router.get("/")
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.business_id == current_user.business_id)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "active": u.active,
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in users
    ]


@router.post("/", status_code=201)
async def invite_user(
    req: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User with this email already exists")

    if req.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be admin, editor, or viewer")

    user = User(
        business_id=current_user.business_id,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=req.role,
    )
    db.add(user)
    await db.flush()

    return {"id": user.id, "email": user.email, "role": user.role, "active": user.active}


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    req: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.business_id == current_user.business_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.role is not None:
        if req.role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = req.role
    if req.active is not None:
        user.active = req.active
    await db.flush()

    return {"id": user.id, "email": user.email, "role": user.role, "active": user.active}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.business_id == current_user.business_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()
    return {"detail": "User deleted"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.business_id == current_user.business_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.active = not user.active
    await db.flush()

    return {"id": user.id, "email": user.email, "active": user.active}
