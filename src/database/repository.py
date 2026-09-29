"""
Tenant-isolated database repository.
Every query enforces org_id equality to guarantee multi-client isolation.
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from src.database.models import ReturnRecord, Override, ImageRecord


class ReturnRepository:
    def __init__(self, db: Session):
        self._db = db

    def save_record(self, record: ReturnRecord) -> ReturnRecord:
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def get_record(self, record_id: str, org_id: str) -> Optional[ReturnRecord]:
        """Tenant-bound fetch: returns None if record belongs to another org_id."""
        return (
            self._db.query(ReturnRecord)
            .filter(
                ReturnRecord.record_id == record_id,
                ReturnRecord.org_id == org_id,
            )
            .first()
        )

    def list_records(
        self,
        org_id: str,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ReturnRecord], int]:
        """Strict tenant-isolated query for listing returns."""
        query = self._db.query(ReturnRecord).filter(ReturnRecord.org_id == org_id)
        if unit_id:
            query = query.filter(ReturnRecord.unit_id == unit_id)
        if status:
            query = query.filter(ReturnRecord.status == status)

        total = query.count()
        records = (
            query.order_by(ReturnRecord.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return records, total

    def update_evidence(
        self,
        record_id: str,
        org_id: str,
        evidence_json: str,
        status: str,
        content_hash: str | None,
    ) -> Optional[ReturnRecord]:
        record = self.get_record(record_id, org_id)
        if not record:
            return None
        record.evidence_json = evidence_json
        record.status = status
        record.content_hash = content_hash
        self._db.commit()
        self._db.refresh(record)
        return record

    def add_override(self, override: Override) -> Override:
        """Appends operator override without modifying past history."""
        self._db.add(override)
        self._db.commit()
        self._db.refresh(override)
        return override

    def list_overrides(self, record_id: str, org_id: str) -> list[Override]:
        return (
            self._db.query(Override)
            .filter(
                Override.record_id == record_id,
                Override.org_id == org_id,
            )
            .order_by(Override.created_at.asc())
            .all()
        )

    def register_image(self, image: ImageRecord) -> ImageRecord:
        self._db.add(image)
        self._db.commit()
        self._db.refresh(image)
        return image

    def get_image(self, image_id: int, org_id: str) -> Optional[ImageRecord]:
        return (
            self._db.query(ImageRecord)
            .filter(
                ImageRecord.id == image_id,
                ImageRecord.org_id == org_id,
            )
            .first()
        )
