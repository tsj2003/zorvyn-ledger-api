from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limit import limiter
from app.database import engine, async_session_factory
from app.models import Base
from app.services.record_ops import purge_stale_idempotency_keys
from app.routes import auth, users, records, dashboard, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create tables if they don't exist (dev convenience — alembic for prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # purge expired idempotency keys on boot
    async with async_session_factory() as session:
        await purge_stale_idempotency_keys(session)
        await session.commit()

    yield

    await engine.dispose()


app = FastAPI(
    title="Finance Data Processing & Access Control API",
    version="1.0.0",
    description="Backend for a finance dashboard with RBAC, audit trails, and idempotent record creation.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def catch_all_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(records.router)
app.include_router(dashboard.router)

