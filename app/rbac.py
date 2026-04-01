from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, UserRole, ROLE_HIERARCHY
from app.security import decode_access_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token_data = decode_access_token(creds.credentials)
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    stmt = select(User).where(User.id == UUID(user_id))
    found = await db.execute(stmt)
    caller = found.scalar_one_or_none()

    if not caller or not caller.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account inactive or not found")
    return caller


def require_role(minimum: UserRole):
    """Factory that returns a dependency enforcing a minimum role level."""
    min_level = ROLE_HIERARCHY[minimum]

    async def _check(caller: User = Depends(get_current_user)) -> User:
        caller_level = ROLE_HIERARCHY.get(caller.role, -1)
        if caller_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{caller.role.value}' insufficient — requires at least '{minimum.value}'",
            )
        return caller

    return _check
