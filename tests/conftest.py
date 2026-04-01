import os
os.environ["RATE_LIMIT_ENABLED"] = "false"

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.database import get_db
from app.main import app
from app.models import Base, UserRole
from app.security import hash_password, create_access_token
from app.models import User
import uuid


# Use SQLite for tests - more portable and doesn't require running Postgres
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with test_session_factory() as session:
        yield session


async def _override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="test_admin@test.com",
        username="test_admin",
        hashed_password=hash_password("admin1234"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def analyst_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="test_analyst@test.com",
        username="test_analyst",
        hashed_password=hash_password("analyst1234"),
        role=UserRole.ANALYST,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="test_viewer@test.com",
        username="test_viewer",
        hashed_password=hash_password("viewer1234"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def make_token(user: User) -> dict:
    token = create_access_token(str(user.id), user.role.value)
    return {"Authorization": f"Bearer {token}"}
