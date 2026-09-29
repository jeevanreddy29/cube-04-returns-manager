"""
Synthetic Parts Catalogue reference loader.
Uses synthetic catalog for fallback lookups, but keeps parts_list open to dynamic input.
"""
from __future__ import annotations

# Catalog derived from synthetic reference data for fallback testing only
SYNTHETIC_PARTS_CATALOGUE: dict[str, list[str]] = {
    "SKU-PUZZLE-500": ["puzzle pieces", "poster"],
    "SKU-LAMP-LED": ["lamp", "usb cable", "manual"],
    "SKU-TOWEL-BLU": ["towel"],
    "SKU-BOTTLE-750": ["bottle", "lid"],
    "SKU-SERUM-30": ["bottle", "dropper", "leaflet"],
    "SKU-PROT-1KG": ["tub", "scoop"],
    "SKU-LEASH-6FT": ["leash"],
    "SKU-CABLE-USBC": ["cable"],
    "SKU-MUG-11": ["mug x2"],
    "SKU-CANDLE-3": ["candle x3", "gift box"],
}


def resolve_expected_parts(sku: str, provided_parts: list[str] | None = None) -> list[str]:
    """If caller specified parts_list, prioritize it; otherwise use catalog baseline."""
    if provided_parts is not None and len(provided_parts) > 0:
        return provided_parts
    return SYNTHETIC_PARTS_CATALOGUE.get(sku, ["primary_unit"])
