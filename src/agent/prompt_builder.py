"""
Multimodal Prompt Builder for single-call batched visual reasoning.
Packages identity verification, completeness check, and condition assessment
into a single multimodal request to minimize latency and operational cost.
"""
from __future__ import annotations

from src.catalogue.condition_scale import get_condition_scale_prompt_text


def build_assessment_prompt(
    ordered_sku: str,
    ordered_asin: str,
    order_id: str,
    parts_list: list[str],
    observed_state: str,
) -> str:
    """
    Constructs the prompt guiding the model to evaluate all three dimensions
    in one unified structured JSON response.
    """
    condition_rules_text = get_condition_scale_prompt_text()
    parts_str = "\n".join(f"  - {part}" for part in parts_list) if parts_list else "  - Primary unit"

    return f"""You are the official Returns Manager Agent operating at an e-commerce fulfillment and returns inspection center.

You are inspecting a customer return product for:
- Ordered SKU: {ordered_sku}
- Ordered ASIN: {ordered_asin}
- Order ID: {order_id}

EXPECTED COMPONENTS / PARTS:
{parts_str}

OPERATOR RAW PHYSICAL OBSERVATION (Initial physical observation by intake personnel):
- observed_state: {observed_state}
Note: observed_state is NOT an official condition grade. You must independently grade condition according to Amazon's guidelines below.

{condition_rules_text}

MANDATORY RULES:
1. Conduct all 3 checks based on the provided images:
   a. IDENTITY: Does the item in the images match the ordered SKU/ASIN ({ordered_sku})?
      - Look for verifiable identifiers: barcode, UPC, EAN, ASIN label, model number, or serial tag.
      - RULE ON VISUAL LIKENESS: If the item visually looks like the expected product but NO strong identifier (barcode/ASIN/serial/model stamp) is readable in the photos, do NOT blindly return PASS. You MUST return UNCERTAIN (e.g. "Visual match but barcode/serial unreadable") to route to operator review and protect against switch fraud.
      - Return FAIL only if the item is clearly a different product, wrong model/color, or an empty box.
   b. COMPLETENESS: Are all expected parts present? Detail any missing components.
   c. CONDITION: Grade using ONLY the Amazon condition scale: New, Like New, Very Good, Good, Acceptable.
2. Use PASS, FAIL, or UNCERTAIN.
3. UNCERTAIN is a first-class outcome. If images are blurry, obscured, missing angles, or ambiguous, you MUST return UNCERTAIN. Do NOT force ambiguous evidence into PASS or FAIL.
4. Output MUST strictly be valid JSON in this exact structure with NO markdown or extraneous commentary:

{{
  "identity": {{
    "verdict": "PASS" | "FAIL" | "UNCERTAIN",
    "confidence": 0.0 - 1.0,
    "detail": "concise rationale based on visual evidence"
  }},
  "completeness": {{
    "verdict": "PASS" | "FAIL" | "UNCERTAIN",
    "parts_present": ["list of parts observed"],
    "parts_missing": ["list of expected parts confirmed missing"],
    "confidence": 0.0 - 1.0,
    "detail": "concise rationale"
  }},
  "condition": {{
    "verdict": "PASS" | "FAIL" | "UNCERTAIN",
    "amazon_grade": "New" | "Like New" | "Very Good" | "Good" | "Acceptable" | null,
    "confidence": 0.0 - 1.0,
    "detail": "concise visual condition assessment referencing specific wear, seals, or packaging"
  }}
}}
"""
