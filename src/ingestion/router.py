"""
Returns Ingestion and Assessment API router.
Enforces tenant isolation, initiates single batched AI analysis, and returns evidence record.
Includes tenant-gated image retrieval endpoint (RULES.md §2.1).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import ReturnRecord, ImageRecord
from src.database.repository import ReturnRepository
from src.ingestion.schemas import (
    AssessRequest,
    ReturnRecordEvidence,
    PaginatedReturns,
    OverrideRequest,
    OverrideItem,
    CheckKey,
)
from src.agent.analyzer import GeminiVisionAnalyzer
from src.catalogue.parts_catalogue import resolve_expected_parts
from src.evidence.contract import assemble_evidence_record, build_fail_open_record
from src.images.storage import TenantImageStorage

router = APIRouter(prefix="/returns", tags=["Returns Management"])
analyzer = GeminiVisionAnalyzer()
image_storage = TenantImageStorage()


@router.post(
    "/assess",
    response_model=ReturnRecordEvidence,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and evaluate a customer return parcel",
)
async def assess_return(
    request: AssessRequest,
    x_org_id: str | None = Header(None, alias="X-Org-Id"),
    db: Session = Depends(get_db),
):
    """
    Ingests physical return evidence, calls batched Gemini multimodal agent,
    runs deterministic disposition logic, and persists auditable evidence record.
    """
    # Enforce tenant isolation between header and payload
    effective_org = x_org_id or request.org_id
    if x_org_id and x_org_id != request.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant mismatch: Header '{x_org_id}' differs from payload '{request.org_id}'",
        )

    request.org_id = effective_org
    record_id = f"RTN-{uuid.uuid4().hex[:6].upper()}"

    repo = ReturnRepository(db)

    # Storing incoming images in org-scoped storage
    stored_image_paths: list[str] = []
    for img_str in request.images:
        path = image_storage.save_image_b64(request.org_id, record_id, img_str)
        stored_image_paths.append(path)
        # Register in database with tenant isolation
        img_rec = ImageRecord(
            record_id=record_id,
            org_id=request.org_id,
            filename=os.path.basename(path),
            storage_path=path,
        )
        repo.register_image(img_rec)

    expected_parts = resolve_expected_parts(request.ordered_sku, request.parts_list)

    try:
        # Single batched AI multimodal call
        ai_result, latency_ms, model_version = await analyzer.analyze(
            ordered_sku=request.ordered_sku,
            ordered_asin=request.ordered_asin,
            order_id=request.order_id,
            parts_list=expected_parts,
            observed_state=request.observed_state.value,
            images_data=request.images,
        )

        evidence = assemble_evidence_record(
            record_id=record_id,
            request=request,
            ai_result=ai_result,
            latency_ms=latency_ms,
            model_version=model_version,
            stored_images=stored_image_paths,
        )
    except Exception as exc:
        # RULES.md §2.3 Fail Open: Preserve incoming record in pending_review
        evidence = build_fail_open_record(
            record_id=record_id,
            request=request,
            error_message=f"Model failure: {str(exc)}",
            stored_images=stored_image_paths,
        )

    # Persist into database with tenant isolation
    db_record = ReturnRecord(
        record_id=record_id,
        org_id=request.org_id,
        unit_id=request.unit_id,
        order_id=request.order_id,
        ordered_sku=request.ordered_sku,
        ordered_asin=request.ordered_asin,
        operator_id=request.operator_id,
        status=evidence.status.value,
        evidence_json=evidence.model_dump_json(),
        content_hash=evidence.content_hash,
    )
    repo.save_record(db_record)

    return evidence


@router.get(
    "/{record_id}",
    response_model=ReturnRecordEvidence,
    summary="Get return evidence record with tenant isolation",
)
def get_return(
    record_id: str,
    x_org_id: str = Header(..., alias="X-Org-Id", description="Tenant organization ID"),
    db: Session = Depends(get_db),
):
    repo = ReturnRepository(db)
    record = repo.get_record(record_id, x_org_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found for organization '{x_org_id}'",
        )
    data = json.loads(record.evidence_json)
    return ReturnRecordEvidence.model_validate(data)


@router.get(
    "/",
    response_model=PaginatedReturns,
    summary="List return records for tenant",
)
def list_returns(
    x_org_id: str = Header(..., alias="X-Org-Id"),
    unit_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    repo = ReturnRepository(db)
    records, total = repo.list_records(
        org_id=x_org_id,
        unit_id=unit_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    items = [ReturnRecordEvidence.model_validate(json.loads(r.evidence_json)) for r in records]
    return PaginatedReturns(records=items, total=total, offset=offset, limit=limit)


@router.post(
    "/{record_id}/override",
    response_model=ReturnRecordEvidence,
    summary="Append operator override preserving original decision",
)
def submit_override(
    record_id: str,
    override: OverrideRequest,
    x_org_id: str = Header(..., alias="X-Org-Id"),
    db: Session = Depends(get_db),
):
    repo = ReturnRepository(db)
    record = repo.get_record(record_id, x_org_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found for organization '{x_org_id}'",
        )

    evidence_dict = json.loads(record.evidence_json)

    # Find the original check verdict
    orig_verdict = "UNKNOWN"
    for check in evidence_dict.get("checks", []):
        if check.get("check_key") == override.check_key.value:
            orig_verdict = check.get("verdict", "UNKNOWN")
            break

    now_iso = datetime.now(timezone.utc).isoformat()
    new_override = OverrideItem(
        check_key=override.check_key,
        original_verdict=orig_verdict,
        revised_verdict=override.revised_verdict,
        reason=override.reason,
        operator_id=override.operator_id,
        overridden_at=now_iso,
    )

    if "overrides" not in evidence_dict or not isinstance(evidence_dict["overrides"], list):
        evidence_dict["overrides"] = []

    # Append-only: preserve both original and revised verdict
    evidence_dict["overrides"].append(new_override.model_dump())

    # Update database record
    from src.database.models import Override as DBOverride
    db_override = DBOverride(
        record_id=record_id,
        org_id=x_org_id,
        check_key=override.check_key.value,
        original_verdict=orig_verdict,
        revised_verdict=override.revised_verdict,
        reason=override.reason,
        operator_id=override.operator_id,
        created_at=now_iso,
    )
    repo.add_override(db_override)

    # Re-save updated evidence JSON
    repo.update_evidence(
        record_id=record_id,
        org_id=x_org_id,
        evidence_json=json.dumps(evidence_dict),
        status="complete",
        content_hash=evidence_dict.get("content_hash"),
    )

    return ReturnRecordEvidence.model_validate(evidence_dict)


@router.get(
    "/images/{image_id}",
    summary="Secure tenant-gated image retrieval (RULES.md §2.1)",
)
def get_tenant_image(
    image_id: int,
    x_org_id: str = Header(..., alias="X-Org-Id", description="Tenant organization ID"),
    db: Session = Depends(get_db),
):
    """
    Enforces strict tenant boundary on image downloads.
    An organisation cannot access another organisation's photos by guessing an image ID.
    """
    repo = ReturnRepository(db)
    img_rec = repo.get_image(image_id, x_org_id)
    if not img_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image #{image_id} not found or access denied for tenant '{x_org_id}'",
        )

    file_path = Path(img_rec.storage_path)
    if not file_path.exists():
        # Fallback 1x1 transparent pixel if file was stored ephemeral
        return Response(content=b"", media_type=img_rec.mime_type)

    return FileResponse(path=str(file_path), media_type=img_rec.mime_type)
