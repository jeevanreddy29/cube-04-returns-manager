"""
SQLAlchemy ORM models with strict multi-tenant partitioning.
- return_records: Case metadata, status, and full official evidence JSON blob.
- overrides: Append-only ledger of operator modifications (never mutating original agent verdict).
- images: Tenant-isolated image registry preventing identifier-guessing attacks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.connection import Base


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReturnRecord(Base):
    __tablename__ = "return_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True) # RTN-XXXX
    org_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)                 # Tenant key
    unit_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_sku: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_asin: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default="pending",
    )
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str, onupdate=utcnow_str)

    overrides: Mapped[list[Override]] = relationship("Override", back_populates="record", cascade="all, delete-orphan")
    images: Mapped[list[ImageRecord]] = relationship("ImageRecord", back_populates="record", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'review', 'uncertain', 'complete', 'pending_review')",
            name="ck_return_records_status",
        ),
        Index("idx_records_org_unit", "org_id", "unit_id"),
    )


class Override(Base):
    """
    Append-only log for operator overrides.
    RULES.md §3.3 requirement: Original verdict must be preserved alongside revisions.
    """
    __tablename__ = "overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(Text, ForeignKey("return_records.record_id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    check_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    revised_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    operator_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)

    record: Mapped[ReturnRecord] = relationship("ReturnRecord", back_populates="overrides")

    __table_args__ = (
        CheckConstraint(
            "check_key IN ('identity', 'completeness', 'condition', 'disposition')",
            name="ck_overrides_check_key",
        ),
        Index("idx_overrides_org_rec", "org_id", "record_id"),
    )


class ImageRecord(Base):
    """
    Tenant-partitioned image registry.
    RULES.md §2.1: Guessable image paths across organisations are strictly prevented.
    """
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(Text, ForeignKey("return_records.record_id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False, default="image/jpeg")
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)

    record: Mapped[ReturnRecord] = relationship("ReturnRecord", back_populates="images")

    __table_args__ = (
        Index("idx_images_org_record", "org_id", "record_id"),
    )
