"""
Integration tests for Fail Open behavior and Operator Overrides.
RULES.md §2.3: Fail Open ensures cases are preserved under pending_review on errors.
RULES.md §3.3: Overrides are append-only and preserve original verdicts.
"""
from __future__ import annotations


def test_append_only_operator_override(client):
    payload = {
        "org_id": "org_demo_alpha",
        "unit_id": "UNIT-0050",
        "order_id": "ORD-DUMMY-50050",
        "ordered_sku": "SKU-PUZZLE-500",
        "ordered_asin": "B0DUMMY729",
        "parts_list": ["puzzle pieces", "poster"],
        "observed_state": "signs_of_use",
        "images": [],
        "operator_id": "op_fatima",
    }
    create_res = client.post("/api/v1/returns/assess", json=payload, headers={"X-Org-Id": "org_demo_alpha"})
    assert create_res.status_code == 201
    rec_id = create_res.json()["record_id"]

    # Submit human override
    override_body = {
        "check_key": "condition",
        "revised_verdict": "Good",
        "reason": "Operator re-inspected under neutral lighting; wear is consistent with Good.",
        "operator_id": "op_lead",
    }
    ovr_res = client.post(f"/api/v1/returns/{rec_id}/override", json=override_body, headers={"X-Org-Id": "org_demo_alpha"})
    assert ovr_res.status_code == 200
    evidence = ovr_res.json()

    # Check that override was recorded and original verdict preserved
    assert len(evidence["overrides"]) == 1
    assert evidence["overrides"][0]["revised_verdict"] == "Good"
    assert evidence["overrides"][0]["original_verdict"] != "Good"
    assert evidence["overrides"][0]["reason"] == override_body["reason"]


def test_ambiguous_evidence_routes_to_pending_review(client):
    payload = {
        "org_id": "org_demo_alpha",
        "unit_id": "UNIT-0092",
        "order_id": "ORD-DUMMY-50092",
        "ordered_sku": "SKU-SERUM-30",
        "ordered_asin": "B0DUMMY031",
        "parts_list": ["bottle", "dropper", "leaflet"],
        "observed_state": "uncertain",
        "images": [],
        "operator_id": "op_fatima",
    }
    res = client.post("/api/v1/returns/assess", json=payload, headers={"X-Org-Id": "org_demo_alpha"})
    assert res.status_code == 201
    record = res.json()

    assert record["status"] == "pending_review"
    assert record["outcome"]["overall_verdict"] == "UNCERTAIN"
    assert record["outcome"]["disposition"] == "pending_review"
