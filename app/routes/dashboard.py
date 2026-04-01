from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, UserRole
from app.rbac import require_role
from app.schemas import DashboardSummary, CategoryBreakdown, MonthlyTrend, RecentActivity
from app.services.dashboard_ops import (
    overall_summary, category_breakdown, monthly_trends, recent_activity,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    viewer: User = Depends(require_role(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    return await overall_summary(db)


@router.get("/category-breakdown", response_model=list[CategoryBreakdown])
async def categories(
    viewer: User = Depends(require_role(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    return await category_breakdown(db)


@router.get("/trends", response_model=list[MonthlyTrend])
async def trends(
    months: int = Query(12, ge=1, le=60),
    viewer: User = Depends(require_role(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    return await monthly_trends(db, months=months)


@router.get("/recent-activity", response_model=list[RecentActivity])
async def recent(
    limit: int = Query(10, ge=1, le=50),
    viewer: User = Depends(require_role(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    return await recent_activity(db, limit=limit)
