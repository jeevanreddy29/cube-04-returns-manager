"""
Evidence Content Hasher.
Computes deterministic SHA-256 fingerprint over canonical JSON.
RULES.md §6.1 compliance: Clear about signature without overclaiming tamper-evidence.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def calculate_content_hash(data: dict[str, Any]) -> str:
    """
    Computes SHA-256 over key-sorted JSON representation.
    Produces repeatable digest for provenance tracking across pipeline managers.
    """
    clean_dict = {k: v for k, v in data.items() if k != "content_hash"}
    canonical_json = json.dumps(clean_dict, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
