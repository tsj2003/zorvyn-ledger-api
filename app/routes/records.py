from uuid import UUID
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, UserRole, RecordType
from app.rbac import require_role
from app.schemas import (
    RecordCreatePayload, RecordUpdatePayload, RecordOut, PaginatedRecords, AuditLogOut,
)
from app.services.record_ops import (
    check_idempotency, store_idempotency, create_record,
    get_record, list_records, update_record, soft_delete_record, ConflictError,
)

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
async def create(
    payload: RecordCreatePayload,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    if idempotency_key:
        cached = await check_idempotency(db, idempotency_key, admin.id)
        if cached:
            return JSONResponse(status_code=cached["code"], content=cached["body"])

    entry = await create_record(
        db,
        amount=payload.amount,
        record_type=payload.record_type,
        category=payload.category,
        record_date=payload.record_date,
        created_by=admin.id,
        description=payload.description,
    )

    serialized = RecordOut.model_validate(entry).model_dump(mode="json")

    if idempotency_key:
        await store_idempotency(db, idempotency_key, admin.id, 201, serialized)

    return entry


@router.get("", response_model=PaginatedRecords)
async def list_all(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    record_type: Optional[RecordType] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    analyst: User = Depends(require_role(UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    records, total = await list_records(
        db, limit=limit, offset=offset,
        record_type=record_type, category=category,
        date_from=date_from, date_to=date_to,
    )
    return PaginatedRecords(records=records, total=total, limit=limit, offset=offset)


@router.get("/{record_id}", response_model=RecordOut)
async def get_single(
    record_id: UUID,
    analyst: User = Depends(require_role(UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    entry = await get_record(db, record_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return entry


@router.patch("/{record_id}", response_model=RecordOut)
async def patch(
    record_id: UUID,
    payload: RecordUpdatePayload,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    try:
        updated = await update_record(
            db, record_id, admin.id,
            expected_updated_at=payload.expected_updated_at,
            amount=payload.amount,
            record_type=payload.record_type,
            category=payload.category,
            description=payload.description,
            record_date=payload.record_date,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return updated


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    record_id: UUID,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    deleted = await soft_delete_record(db, record_id, admin.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
