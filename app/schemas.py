from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models import RecordType, UserRole


# ── Auth ─────────────────────────────────────────────────

class RegisterPayload(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Users ────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdatePayload(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# ── Financial Records ────────────────────────────────────

class RecordCreatePayload(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    record_type: RecordType
    category: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    record_date: date

    @field_validator("amount")
    @classmethod
    def enforce_two_decimals(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))


class RecordUpdatePayload(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    record_type: Optional[RecordType] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    record_date: Optional[date] = None
    expected_updated_at: datetime  # optimistic concurrency token

    @field_validator("amount")
    @classmethod
    def enforce_two_decimals(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            return v.quantize(Decimal("0.01"))
        return v


class RecordOut(BaseModel):
    id: UUID
    amount: Decimal
    record_type: RecordType
    category: str
    description: Optional[str]
    record_date: date
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "json_encoders": {Decimal: str}}


class RecordFilters(BaseModel):
    record_type: Optional[RecordType] = None
    category: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class PaginatedRecords(BaseModel):
    records: list[RecordOut]
    total: int
    limit: int
    offset: int


# ── Dashboard ────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_balance: Decimal
    record_count: int

    model_config = {"json_encoders": {Decimal: str}}


class CategoryBreakdown(BaseModel):
    category: str
    total: Decimal
    record_type: RecordType

    model_config = {"json_encoders": {Decimal: str}}


class MonthlyTrend(BaseModel):
    year: int
    month: int
    income: Decimal
    expenses: Decimal

    model_config = {"json_encoders": {Decimal: str}}


class RecentActivity(BaseModel):
    id: UUID
    amount: Decimal
    record_type: RecordType
    category: str
    record_date: date
    created_at: datetime

    model_config = {"from_attributes": True, "json_encoders": {Decimal: str}}


# ── Audit ────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: UUID
    record_id: UUID
    action: str
    changed_by: UUID
    old_payload: Optional[dict]
    new_payload: Optional[dict]
    changed_at: datetime

    model_config = {"from_attributes": True}


# ── Health ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    db: str
