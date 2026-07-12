from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.models.business import Business

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    business_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: str | None = None


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    from app.core.security import get_password_hash

    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    business = Business(name=req.business_name)
    db.add(business)
    await db.flush()

    user = User(
        business_id=business.id,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role="admin",
    )
    db.add(user)
    await db.flush()

    return {"user_id": user.id, "email": user.email}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id), "role": user.role, "business_id": user.business_id})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,
    }


@router.post("/refresh")
async def refresh_token(token_data: dict):
    from app.core.security import decode_token, create_access_token
    payload = decode_token(token_data.get("refresh_token", ""))
    new_access = create_access_token({"sub": payload.sub, "role": payload.role, "business_id": payload.business_id})
    return {"access_token": new_access, "token_type": "bearer", "expires_in": 3600}
