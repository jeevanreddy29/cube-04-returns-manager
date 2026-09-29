"""
Integration tests for Tenant Isolation (RULES.md §2.1).
Guarantees org_demo_alpha and org_demo_bravo data remain strictly isolated.
"""
from __future__ import annotations


def test_tenant_data_isolation(client):
    # 1. Create record for org_demo_alpha
    payload_alpha = {
        "org_id": "org_demo_alpha",
        "unit_id": "UNIT-0016",
        "order_id": "ORD-DUMMY-50016",
        "ordered_sku": "SKU-TOWEL-BLU",
        "ordered_asin": "B0DUMMY600",
        "parts_list": ["towel"],
        "observed_state": "opened_unused",
        "images": [],
        "operator_id": "op_ben",
    }
    res_alpha = client.post("/api/v1/returns/assess", json=payload_alpha, headers={"X-Org-Id": "org_demo_alpha"})
    assert res_alpha.status_code == 201
    rec_id_alpha = res_alpha.json()["record_id"]

    # 2. Verify org_demo_bravo receives 404/forbidden attempting to view alpha's record
    res_bravo_view = client.get(f"/api/v1/returns/{rec_id_alpha}", headers={"X-Org-Id": "org_demo_bravo"})
    assert res_bravo_view.status_code == 404

    # 3. Verify org_demo_bravo cannot list or see rows belonging to alpha
    res_bravo_list = client.get("/api/v1/returns/", headers={"X-Org-Id": "org_demo_bravo"})
    assert res_bravo_list.status_code == 200
    assert res_bravo_list.json()["total"] == 0

    # 4. Verify alpha can access their record successfully
    res_alpha_view = client.get(f"/api/v1/returns/{rec_id_alpha}", headers={"X-Org-Id": "org_demo_alpha"})
    assert res_alpha_view.status_code == 200
    assert res_alpha_view.json()["record_id"] == rec_id_alpha
