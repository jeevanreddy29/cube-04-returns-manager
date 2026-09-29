"""
Pydantic API and Evidence Contract Schemas.
Faithfully follows official evidence contract requirements from RULES.md and README.md.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class ObservedState(str, Enum):
    """Raw physical observation made by warehouse operator."""
    factory_sealed = "factory_sealed"
    opened_unused = "opened_unused"
    signs_of_use = "signs_of_use"
    damaged = "damaged"
    empty_box = "empty_box"
    uncertain = "uncertain"


class Verdict(str, Enum):
    """Core verdicts. UNCERTAIN is a first-class outcome, never a low-confidence PASS."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class RecordStatus(str, Enum):
    pending = "pending"
    review = "review"
    uncertain = "uncertain"
    complete = "complete"
    pending_review = "pending_review"


class Disposition(str, Enum):
    restock = "restock"
    refurbish = "refurbish"
    liquidate = "liquidate"
    dispose = "dispose"
    pending_review = "pending_review"


class CheckKey(str, Enum):
    identity = "identity"
    completeness = "completeness"
    condition = "condition"
    disposition = "disposition"


# --- Sub-components of the Official Evidence Record ---

class CheckResult(BaseModel):
    check_key: CheckKey
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    detail: str
    model_version: str
    latency_ms: int = Field(ge=0)


class Outcome(BaseModel):
    identity: Verdict
    completeness: Verdict
    parts_missing: list[str] = Field(default_factory=list)
    condition: Optional[str] = None       # Official Amazon grade or None if UNCERTAIN
    observed_state: str                   # Preserved operator input
    disposition: Disposition
    overall_verdict: Verdict


class OverrideItem(BaseModel):
    check_key: CheckKey
    original_verdict: str
    revised_verdict: str
    reason: str
    operator_id: str
    overridden_at: str


class Subject(BaseModel):
    unit_id: str
    order_id: Optional[str] = None
    ordered_sku: Optional[str] = None
    ordered_asin: Optional[str] = None


class ReturnRecordEvidence(BaseModel):
    """The canonical evidence contract consumed downstream by Recovery Manager."""
    record_id: str
    schema_version: str = "1.0"
    organization_id: str
    client_id: Optional[str] = None
    agent: str
    subject: Subject
    captured_at: str
    operator_label: str
    images: list[str] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    outcome: Optional[Outcome] = None
    overrides: list[OverrideItem] = Field(default_factory=list)
    status: RecordStatus
    content_hash: Optional[str] = None
    error_message: Optional[str] = None


# --- API Request / Response schemas ---

class AssessRequest(BaseModel):
    org_id: str = Field(description="Tenant ID (e.g. org_demo_alpha or org_demo_bravo)")
    unit_id: str
    order_id: str
    ordered_sku: str
    ordered_asin: str
    parts_list: list[str] = Field(default_factory=list)
    observed_state: ObservedState
    images: list[str] = Field(default_factory=list, description="Base64 or image paths")
    operator_id: str
    client_id: Optional[str] = None

    @field_validator("images", mode="before")
    @classmethod
    def check_image_cap(cls, v: Any):
        if isinstance(v, list) and len(v) > 10:
            raise ValueError("Exceeded maximum limit of 10 images per assessment")
        return v


class OverrideRequest(BaseModel):
    check_key: CheckKey
    revised_verdict: str
    reason: str = Field(min_length=3, description="Audit justification for human override")
    operator_id: str


class PaginatedReturns(BaseModel):
    records: list[ReturnRecordEvidence]
    total: int
    offset: int
    limit: int
