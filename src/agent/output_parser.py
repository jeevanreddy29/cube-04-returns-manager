"""
AI Agent output parser and validator.
Enforces that model responses strictly respect the Amazon condition scale
and valid verdict enumerations.
"""
from __future__ import annotations

import json
from typing import Any
from src.catalogue.condition_scale import is_valid_condition_grade
from src.ingestion.schemas import Verdict


def parse_and_validate_ai_response(raw_text: str) -> dict[str, Any]:
    """
    Parses JSON from Gemini multimodal response and validates fields.
    Falls back gracefully if LLM output requires sanitization.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    data = json.loads(cleaned)

    # 1. Identity validation
    id_data = data.get("identity", {})
    id_verdict_str = str(id_data.get("verdict", "UNCERTAIN")).upper()
    if id_verdict_str not in ("PASS", "FAIL", "UNCERTAIN"):
        id_data["verdict"] = "UNCERTAIN"
    else:
        id_data["verdict"] = id_verdict_str
    id_data["confidence"] = max(0.0, min(1.0, float(id_data.get("confidence", 0.5))))
    id_data["detail"] = str(id_data.get("detail", "Identity assessment generated."))
    data["identity"] = id_data

    # 2. Completeness validation
    comp_data = data.get("completeness", {})
    comp_verdict_str = str(comp_data.get("verdict", "UNCERTAIN")).upper()
    if comp_verdict_str not in ("PASS", "FAIL", "UNCERTAIN"):
        comp_data["verdict"] = "UNCERTAIN"
    else:
        comp_data["verdict"] = comp_verdict_str
    comp_data["confidence"] = max(0.0, min(1.0, float(comp_data.get("confidence", 0.5))))
    if not isinstance(comp_data.get("parts_missing"), list):
        comp_data["parts_missing"] = []
    comp_data["detail"] = str(comp_data.get("detail", "Completeness assessment generated."))
    data["completeness"] = comp_data

    # 3. Condition assessment validation (Strict Amazon condition scale check)
    cond_data = data.get("condition", {})
    cond_verdict_str = str(cond_data.get("verdict", "UNCERTAIN")).upper()
    if cond_verdict_str not in ("PASS", "FAIL", "UNCERTAIN"):
        cond_data["verdict"] = "UNCERTAIN"
    else:
        cond_data["verdict"] = cond_verdict_str

    raw_grade = cond_data.get("amazon_grade")
    if raw_grade:
        raw_grade = str(raw_grade).strip().title()
        if not is_valid_condition_grade(raw_grade):
            # Model hallucinated non-standard grade -> treat as UNCERTAIN
            cond_data["verdict"] = "UNCERTAIN"
            cond_data["amazon_grade"] = None
            cond_data["detail"] = f"Model proposed invalid grade '{raw_grade}'. Defaulted to UNCERTAIN."
        else:
            cond_data["amazon_grade"] = raw_grade
    else:
        cond_data["amazon_grade"] = None

    cond_data["confidence"] = max(0.0, min(1.0, float(cond_data.get("confidence", 0.5))))
    cond_data["detail"] = str(cond_data.get("detail", "Condition grading complete."))
    data["condition"] = cond_data

    return data
