"""
Unit tests for deterministic disposition engine and condition scale loader.
"""
from __future__ import annotations

from src.ingestion.schemas import Verdict, Disposition
from src.decisions.disposition_rules import evaluate_disposition
from src.catalogue.condition_scale import is_valid_condition_grade, get_valid_condition_grades


def test_condition_scale_grades():
    grades = get_valid_condition_grades()
    assert "New" in grades
    assert "Like New" in grades
    assert "Very Good" in grades
    assert "Good" in grades
    assert "Acceptable" in grades
    assert not is_valid_condition_grade("Brand New Refurbished") # Non-standard grade


def test_disposition_identity_fail_routes_to_pending_review():
    disp, overall = evaluate_disposition(
        identity_verdict=Verdict.FAIL,
        completeness_verdict=Verdict.PASS,
        condition_verdict=Verdict.PASS,
        amazon_grade="New",
        observed_state="opened_unused",
        parts_missing=[],
    )
    assert disp == Disposition.pending_review
    assert overall == Verdict.FAIL


def test_disposition_uncertain_first_class():
    disp, overall = evaluate_disposition(
        identity_verdict=Verdict.PASS,
        completeness_verdict=Verdict.PASS,
        condition_verdict=Verdict.UNCERTAIN,
        amazon_grade=None,
        observed_state="uncertain",
        parts_missing=[],
    )
    assert disp == Disposition.pending_review
    assert overall == Verdict.UNCERTAIN


def test_disposition_restock_for_new_and_complete():
    disp, overall = evaluate_disposition(
        identity_verdict=Verdict.PASS,
        completeness_verdict=Verdict.PASS,
        condition_verdict=Verdict.PASS,
        amazon_grade="Like New",
        observed_state="opened_unused",
        parts_missing=[],
    )
    assert disp == Disposition.restock
    assert overall == Verdict.PASS


def test_disposition_refurbish_when_parts_missing():
    disp, overall = evaluate_disposition(
        identity_verdict=Verdict.PASS,
        completeness_verdict=Verdict.FAIL,
        condition_verdict=Verdict.PASS,
        amazon_grade="Very Good",
        observed_state="opened_unused",
        parts_missing=["cable"],
    )
    assert disp == Disposition.refurbish
    assert overall == Verdict.FAIL


def test_disposition_empty_box_routes_to_dispose():
    disp, overall = evaluate_disposition(
        identity_verdict=Verdict.PASS,
        completeness_verdict=Verdict.PASS,
        condition_verdict=Verdict.PASS,
        amazon_grade="Acceptable",
        observed_state="empty_box",
        parts_missing=[],
    )
    assert disp == Disposition.dispose
