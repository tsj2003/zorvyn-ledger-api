import json
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    FinancialRecord, RecordAuditLog, IdempotencyKey,
    AuditAction, RecordType, User,
)


def _record_to_dict(rec: FinancialRecord) -> dict:
    return {
        "id": str(rec.id),
        "amount": str(rec.amount),
        "record_type": rec.record_type.value,
        "category": rec.category,
        "description": rec.description,
        "record_date": rec.record_date.isoformat(),
    }


def _active_records():
    return select(FinancialRecord).where(FinancialRecord.deleted_at.is_(None))


async def check_idempotency(db: AsyncSession, key: str, user_id: UUID) -> Optional[dict]:
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.key == key, IdempotencyKey.user_id == user_id
    )
    row = await db.execute(stmt)
    found = row.scalar_one_or_none()
    if found:
        return {"code": found.response_code, "body": found.response_body}
    return None


async def store_idempotency(
    db: AsyncSession, key: str, user_id: UUID, code: int, body: dict
):
    entry = IdempotencyKey(key=key, user_id=user_id, response_code=code, response_body=body)
    db.add(entry)
    await db.flush()


async def purge_stale_idempotency_keys(db: AsyncSession):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    await db.execute(delete(IdempotencyKey).where(IdempotencyKey.created_at < cutoff))
    await db.flush()


async def _write_audit(
    db: AsyncSession,
    record_id: UUID,
    action: AuditAction,
    changed_by: UUID,
    old_payload: Optional[dict] = None,
    new_payload: Optional[dict] = None,
):
    log = RecordAuditLog(
        record_id=record_id,
        action=action,
        changed_by=changed_by,
        old_payload=old_payload,
        new_payload=new_payload,
    )
    db.add(log)


async def create_record(
    db: AsyncSession,
    amount: Decimal,
    record_type: RecordType,
    category: str,
    record_date: date,
    created_by: UUID,
    description: Optional[str] = None,
) -> FinancialRecord:
    entry = FinancialRecord(
        amount=amount,
        record_type=record_type,
        category=category,
        description=description,
        record_date=record_date,
        created_by=created_by,
    )
    db.add(entry)
    await db.flush()

    await _write_audit(db, entry.id, AuditAction.CREATE, created_by, new_payload=_record_to_dict(entry))
    return entry


async def get_record(db: AsyncSession, record_id: UUID) -> Optional[FinancialRecord]:
    stmt = _active_records().where(FinancialRecord.id == record_id)
    row = await db.execute(stmt)
    return row.scalar_one_or_none()


async def list_records(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    record_type: Optional[RecordType] = None,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[list[FinancialRecord], int]:
    stmt = _active_records()
    count_stmt = select(func.count()).select_from(FinancialRecord).where(FinancialRecord.deleted_at.is_(None))

    if record_type:
        stmt = stmt.where(FinancialRecord.record_type == record_type)
        count_stmt = count_stmt.where(FinancialRecord.record_type == record_type)
    if category:
        stmt = stmt.where(FinancialRecord.category == category)
        count_stmt = count_stmt.where(FinancialRecord.category == category)
    if date_from:
        stmt = stmt.where(FinancialRecord.record_date >= date_from)
        count_stmt = count_stmt.where(FinancialRecord.record_date >= date_from)
    if date_to:
        stmt = stmt.where(FinancialRecord.record_date <= date_to)
        count_stmt = count_stmt.where(FinancialRecord.record_date <= date_to)

    stmt = stmt.order_by(FinancialRecord.record_date.desc()).limit(limit).offset(offset)

    total = (await db.execute(count_stmt)).scalar() or 0
    rows = await db.execute(stmt)
    return list(rows.scalars().all()), total


async def update_record(
    db: AsyncSession,
    record_id: UUID,
    caller_id: UUID,
    expected_updated_at: datetime,
    amount: Optional[Decimal] = None,
    record_type: Optional[RecordType] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    record_date: Optional[date] = None,
) -> FinancialRecord:
    target = await get_record(db, record_id)
    if not target:
        raise ValueError("Record not found")

    # optimistic concurrency: reject if stale (with tolerance for db precision differences)
    # SQLite and PostgreSQL have different timestamp precision and timezone handling
    def _normalize_ts(ts):
        if ts is None:
            return None
        # Ensure both timestamps are timezone-aware for fair comparison
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        # Truncate to milliseconds (remove microseconds) to handle db precision differences
        return ts.replace(microsecond=(ts.microsecond // 1000) * 1000)
    
    db_ts = _normalize_ts(target.updated_at)
    expected_ts = _normalize_ts(expected_updated_at)
    
    if db_ts != expected_ts:
        raise ConflictError("Record was modified by another request — refresh and retry")

    old_snapshot = _record_to_dict(target)

    if amount is not None:
        target.amount = amount
    if record_type is not None:
        target.record_type = record_type
    if category is not None:
        target.category = category
    if description is not None:
        target.description = description
    if record_date is not None:
        target.record_date = record_date

    await db.flush()

    await _write_audit(
        db, target.id, AuditAction.UPDATE, caller_id,
        old_payload=old_snapshot, new_payload=_record_to_dict(target),
    )
    return target


async def soft_delete_record(db: AsyncSession, record_id: UUID, caller_id: UUID) -> bool:
    target = await get_record(db, record_id)
    if not target:
        return False

    old_snapshot = _record_to_dict(target)
    target.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    await _write_audit(db, target.id, AuditAction.DELETE, caller_id, old_payload=old_snapshot)
    return True


class ConflictError(Exception):
    pass
