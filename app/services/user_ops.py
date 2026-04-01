from uuid import UUID
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserRole
from app.security import hash_password


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    raw_password: str,
    role: UserRole = UserRole.VIEWER,
) -> User:
    existing = await db.execute(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing.scalar_one_or_none():
        raise ValueError("Email or username already taken")

    new_user = User(
        email=email,
        username=username,
        hashed_password=hash_password(raw_password),
        role=role,
    )
    db.add(new_user)
    await db.flush()
    return new_user


async def list_users(
    db: AsyncSession,
    role_filter: Optional[UserRole] = None,
    include_inactive: bool = False,
) -> list[User]:
    stmt = select(User)
    if not include_inactive:
        stmt = stmt.where(User.is_active == True)
    if role_filter:
        stmt = stmt.where(User.role == role_filter)
    stmt = stmt.order_by(User.created_at.desc())
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    row = await db.execute(stmt)
    return row.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    target: User,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
) -> User:
    if role is not None:
        target.role = role
    if is_active is not None:
        target.is_active = is_active
    await db.flush()
    return target
