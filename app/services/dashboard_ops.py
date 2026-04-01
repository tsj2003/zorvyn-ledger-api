from decimal import Decimal
from sqlalchemy import select, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import FinancialRecord, RecordType


def _live():
    return FinancialRecord.deleted_at.is_(None)


async def overall_summary(db: AsyncSession) -> dict:
    stmt = select(
        func.coalesce(
            func.sum(case((FinancialRecord.record_type == RecordType.INCOME, FinancialRecord.amount))),
            Decimal("0"),
        ).label("total_income"),
        func.coalesce(
            func.sum(case((FinancialRecord.record_type == RecordType.EXPENSE, FinancialRecord.amount))),
            Decimal("0"),
        ).label("total_expenses"),
        func.count().label("record_count"),
    ).where(_live())

    row = (await db.execute(stmt)).one()
    return {
        "total_income": row.total_income,
        "total_expenses": row.total_expenses,
        "net_balance": row.total_income - row.total_expenses,
        "record_count": row.record_count,
    }


async def category_breakdown(db: AsyncSession) -> list[dict]:
    stmt = (
        select(
            FinancialRecord.category,
            FinancialRecord.record_type,
            func.sum(FinancialRecord.amount).label("total"),
        )
        .where(_live())
        .group_by(FinancialRecord.category, FinancialRecord.record_type)
        .order_by(func.sum(FinancialRecord.amount).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [{"category": r.category, "record_type": r.record_type, "total": r.total} for r in rows]


async def monthly_trends(db: AsyncSession, months: int = 12) -> list[dict]:
    stmt = (
        select(
            extract("year", FinancialRecord.record_date).label("yr"),
            extract("month", FinancialRecord.record_date).label("mo"),
            func.coalesce(
                func.sum(case((FinancialRecord.record_type == RecordType.INCOME, FinancialRecord.amount))),
                Decimal("0"),
            ).label("income"),
            func.coalesce(
                func.sum(case((FinancialRecord.record_type == RecordType.EXPENSE, FinancialRecord.amount))),
                Decimal("0"),
            ).label("expenses"),
        )
        .where(_live())
        .group_by("yr", "mo")
        .order_by("yr", "mo")
    )
    rows = (await db.execute(stmt)).all()
    return [{"year": int(r.yr), "month": int(r.mo), "income": r.income, "expenses": r.expenses} for r in rows]


async def recent_activity(db: AsyncSession, limit: int = 10) -> list[FinancialRecord]:
    stmt = (
        select(FinancialRecord)
        .where(_live())
        .order_by(FinancialRecord.created_at.desc())
        .limit(limit)
    )
    rows = await db.execute(stmt)
    return list(rows.scalars().all())
