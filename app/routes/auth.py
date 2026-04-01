from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.rate_limit import limiter
from app.models import User
from app.schemas import RegisterPayload, LoginPayload, TokenResponse, UserOut
from app.security import verify_password, create_access_token
from app.services.user_ops import create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, payload: RegisterPayload, db: AsyncSession = Depends(get_db)):
    try:
        new_user = await create_user(db, payload.email, payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return new_user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginPayload, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    row = await db.execute(stmt)
    matched_user = row.scalar_one_or_none()

    if not matched_user or not verify_password(payload.password, matched_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not matched_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    token = create_access_token(str(matched_user.id), matched_user.role.value)
    return TokenResponse(access_token=token)

