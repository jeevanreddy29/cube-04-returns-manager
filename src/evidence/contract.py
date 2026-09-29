"""
Evidence Contract Record Builder.
Packages inputs, check results, deterministic disposition outcomes,
and hash integrity signatures into the canonical schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from src.ingestion.schemas import (
    AssessRequest,
    CheckResult,
    CheckKey,
    Verdict,
    Outcome,
    ReturnRecordEvidence,
    RecordStatus,
    Subject,
    Disposition,
)
from src.evidence.hasher import calculate_content_hash
from src.decisions.disposition_rules import evaluate_disposition


def assemble_evidence_record(
    record_id: str,
    request: AssessRequest,
    ai_result: dict,
    latency_ms: int,
    model_version: str,
    stored_images: list[str] | None = None,
) -> ReturnRecordEvidence:
    """
    Combines AI output + deterministic decision rules into official evidence contract.
    """
    id_data = ai_result.get("identity", {})
    comp_data = ai_result.get("completeness", {})
    cond_data = ai_result.get("condition", {})

    id_verdict = Verdict(id_data.get("verdict", "UNCERTAIN"))
    comp_verdict = Verdict(comp_data.get("verdict", "UNCERTAIN"))
    cond_verdict = Verdict(cond_data.get("verdict", "UNCERTAIN"))
    amazon_grade = cond_data.get("amazon_grade")
    parts_missing = comp_data.get("parts_missing", [])

    # Evaluate deterministic disposition based on authoritative condition guidelines
    disposition, overall_verdict = evaluate_disposition(
        identity_verdict=id_verdict,
        completeness_verdict=comp_verdict,
        condition_verdict=cond_verdict,
        amazon_grade=amazon_grade,
        observed_state=request.observed_state.value,
        parts_missing=parts_missing,
        condition_confidence=cond_data.get("confidence", 1.0),
    )

    checks = [
        CheckResult(
            check_key=CheckKey.identity,
            verdict=id_verdict,
            confidence=float(id_data.get("confidence", 0.5)),
            detail=str(id_data.get("detail", "")),
            model_version=model_version,
            latency_ms=latency_ms,
        ),
        CheckResult(
            check_key=CheckKey.completeness,
            verdict=comp_verdict,
            confidence=float(comp_data.get("confidence", 0.5)),
            detail=str(comp_data.get("detail", "")),
            model_version=model_version,
            latency_ms=latency_ms,
        ),
        CheckResult(
            check_key=CheckKey.condition,
            verdict=cond_verdict,
            confidence=float(cond_data.get("confidence", 0.5)),
            detail=str(cond_data.get("detail", "")),
            model_version=model_version,
            latency_ms=latency_ms,
        ),
        CheckResult(
            check_key=CheckKey.disposition,
            verdict=overall_verdict,
            confidence=float(cond_data.get("confidence", 0.5)),
            detail=f"Deterministic decision: {disposition.value}",
            model_version="rules-engine-v1",
            latency_ms=1,
        )
    ]

    outcome = Outcome(
        identity=id_verdict,
        completeness=comp_verdict,
        parts_missing=parts_missing,
        condition=amazon_grade,
        observed_state=request.observed_state.value,
        disposition=disposition,
        overall_verdict=overall_verdict,
    )

    # Determine status
    if overall_verdict == Verdict.UNCERTAIN or disposition == Disposition.pending_review:
        status = RecordStatus.pending_review
    else:
        status = RecordStatus.complete

    captured_at = datetime.now(timezone.utc).isoformat()

    evidence = ReturnRecordEvidence(
        record_id=record_id,
        schema_version="1.0",
        organization_id=request.org_id,
        client_id=request.client_id,
        agent="returns-manager-v1",
        subject=Subject(
            unit_id=request.unit_id,
            order_id=request.order_id,
            ordered_sku=request.ordered_sku,
            ordered_asin=request.ordered_asin,
        ),
        captured_at=captured_at,
        operator_label=request.operator_id,
        images=stored_images or [],
        checks=checks,
        outcome=outcome,
        overrides=[],
        status=status,
    )

    # Attach computed SHA-256 fingerprint
    evidence.content_hash = calculate_content_hash(evidence.model_dump())
    return evidence


def build_fail_open_record(
    record_id: str,
    request: AssessRequest,
    error_message: str,
    stored_images: list[str] | None = None,
) -> ReturnRecordEvidence:
    """
    RULES.md §2.3 Fail Open:
    Preserves all capture and incoming data under pending_review on dependency failure.
    """
    captured_at = datetime.now(timezone.utc).isoformat()
    evidence = ReturnRecordEvidence(
        record_id=record_id,
        schema_version="1.0",
        organization_id=request.org_id,
        client_id=request.client_id,
        agent="returns-manager-v1",
        subject=Subject(
            unit_id=request.unit_id,
            order_id=request.order_id,
            ordered_sku=request.ordered_sku,
            ordered_asin=request.ordered_asin,
        ),
        captured_at=captured_at,
        operator_label=request.operator_id,
        images=stored_images or [],
        checks=[
            CheckResult(
                check_key=CheckKey.identity,
                verdict=Verdict.UNCERTAIN,
                confidence=0.0,
                detail=f"Analysis interrupted: {error_message}",
                model_version="system-fail-open",
                latency_ms=0,
            )
        ],
        outcome=Outcome(
            identity=Verdict.UNCERTAIN,
            completeness=Verdict.UNCERTAIN,
            parts_missing=[],
            condition=None,
            observed_state=request.observed_state.value,
            disposition=Disposition.pending_review,
            overall_verdict=Verdict.UNCERTAIN,
        ),
        overrides=[],
        status=RecordStatus.pending_review,
        error_message=error_message,
    )
    evidence.content_hash = calculate_content_hash(evidence.model_dump())
    return evidence
