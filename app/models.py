import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Enum as SAEnum,
    ForeignKey, Index, Integer, JSON, Numeric, SmallInteger, String, Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


ROLE_HIERARCHY = {UserRole.VIEWER: 0, UserRole.ANALYST: 1, UserRole.ADMIN: 2}


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class RecordType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    records = relationship("FinancialRecord", back_populates="creator", lazy="selectin")

    __table_args__ = (
        Index("ix_users_role", "role"),
    )


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric(15, 2), nullable=False)
    record_type = Column(SAEnum(RecordType, name="record_type_enum"), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    record_date = Column(Date, nullable=False)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", back_populates="records")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_positive_amount"),
        Index("ix_records_type_date", "record_type", "record_date"),
        Index("ix_records_category", "category"),
        Index("ix_records_created_by", "created_by"),
        Index("ix_records_active", "deleted_at", postgresql_where=text("deleted_at IS NULL")),
    )


class RecordAuditLog(Base):
    __tablename__ = "record_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("financial_records.id"), nullable=False)
    action = Column(SAEnum(AuditAction, name="audit_action_enum"), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    old_payload = Column(JSON, nullable=True)
    new_payload = Column(JSON, nullable=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_audit_record_id", "record_id"),
        Index("ix_audit_changed_at", "changed_at"),
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    response_code = Column(SmallInteger, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
