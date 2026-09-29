"""
Authoritative Amazon condition scale loader and validator.
Decouples raw operator observed_state from Amazon official grading rules.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "condition_scale.json"


@lru_cache(maxsize=1)
def load_condition_scale() -> dict[str, Any]:
    """Reads and caches authoritative condition scale definition from JSON."""
    if not CONFIG_PATH.exists():
        # Fallback safeguard if config path is moved
        return {
            "version": "2024-default-fallback",
            "source": "https://www.amazon.com/gp/help/customer/display.html?nodeId=201889220",
            "valid_grades": ["New", "Like New", "Very Good", "Good", "Acceptable"],
            "grades": [
                {"grade": "New", "description": "Brand-new, unopened, pristine."},
                {"grade": "Like New", "description": "Apparently untouched, perfect condition."},
                {"grade": "Very Good", "description": "Limited use, complete and operational."},
                {"grade": "Good", "description": "Consistent use, functional with moderate wear."},
                {"grade": "Acceptable", "description": "Fairly worn, scratches/dents, functional."}
            ]
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_valid_condition_grades() -> list[str]:
    return load_condition_scale().get("valid_grades", [])


def is_valid_condition_grade(grade: str | None) -> bool:
    if grade is None:
        return True
    return grade in get_valid_condition_grades()


def get_condition_scale_prompt_text() -> str:
    """Formats the authoritative condition definitions for LLM system prompt insertion."""
    scale = load_condition_scale()
    lines = [
        "OFFICIAL AMAZON CONDITION GUIDELINES (Strict scale):"
    ]
    for item in scale.get("grades", []):
        lines.append(f"- {item['grade']}: {item['description']}")
    return "\n".join(lines)
