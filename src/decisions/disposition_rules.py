"""
Deterministic Disposition Decision Layer.
Pure Python business logic. No secondary LLM calls.
RULES.md & README requirements:
- PASS, FAIL, UNCERTAIN are first-class verdicts.
- Identity FAIL aborts operational routing to pending_review.
- Any UNCERTAIN check leads to pending_review unless sufficient verified safety margins exist.
- Valid Amazon condition scale grades map to restock, refurbish, liquidate, or dispose.
"""
from __future__ import annotations

from typing import Optional
from src.ingestion.schemas import Verdict, Disposition, Outcome, ObservedState


def evaluate_disposition(
    identity_verdict: Verdict,
    completeness_verdict: Verdict,
    condition_verdict: Verdict,
    amazon_grade: Optional[str],
    observed_state: str,
    parts_missing: list[str],
    condition_confidence: float = 1.0,
) -> tuple[Disposition, Verdict]:
    """
    Deterministic resolution tree returning (disposition, overall_verdict).
    """
    # 1. Identity failure (wrong item returned or fraudulent return)
    if identity_verdict == Verdict.FAIL:
        return Disposition.pending_review, Verdict.FAIL

    # 2. Identity uncertain
    if identity_verdict == Verdict.UNCERTAIN:
        return Disposition.pending_review, Verdict.UNCERTAIN

    # 3. Completeness uncertain
    if completeness_verdict == Verdict.UNCERTAIN:
        return Disposition.pending_review, Verdict.UNCERTAIN

    # 4. Condition uncertain or missing grade
    if condition_verdict == Verdict.UNCERTAIN or not amazon_grade:
        return Disposition.pending_review, Verdict.UNCERTAIN

    # Overall check verdict rollup
    checks = [identity_verdict, completeness_verdict, condition_verdict]
    if any(c == Verdict.FAIL for c in checks):
        overall_verdict = Verdict.FAIL
    elif any(c == Verdict.UNCERTAIN for c in checks):
        overall_verdict = Verdict.UNCERTAIN
    else:
        overall_verdict = Verdict.PASS

    # 5. Observed state physical safety checks
    if observed_state == ObservedState.empty_box.value:
        return Disposition.dispose, Verdict.FAIL

    if observed_state == ObservedState.damaged.value and (amazon_grade == "Acceptable" or not amazon_grade):
        return Disposition.dispose, Verdict.FAIL

    # 6. Authoritative Amazon condition grade disposition mapping
    grade_clean = amazon_grade.strip().title()

    if grade_clean == "New":
        if completeness_verdict == Verdict.PASS:
            return Disposition.restock, overall_verdict
        else:
            return Disposition.refurbish, overall_verdict

    elif grade_clean == "Like New":
        if completeness_verdict == Verdict.PASS:
            return Disposition.restock, overall_verdict
        else:
            return Disposition.refurbish, overall_verdict

    elif grade_clean == "Very Good":
        if completeness_verdict == Verdict.PASS:
            return Disposition.restock, overall_verdict
        else:
            return Disposition.refurbish, overall_verdict

    elif grade_clean == "Good":
        # Noticeable wear; route to refurbish or liquidate
        if completeness_verdict == Verdict.PASS:
            return Disposition.refurbish, overall_verdict
        else:
            return Disposition.refurbish, overall_verdict

    elif grade_clean == "Acceptable":
        # Fairly worn / heavy use: salvage value via liquidation
        return Disposition.liquidate, overall_verdict

    # Default fallback safety
    return Disposition.pending_review, Verdict.UNCERTAIN
