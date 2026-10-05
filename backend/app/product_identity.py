"""Canonical product/supplier identity helpers shared by API and ETL."""
from decimal import Decimal, InvalidOperation
import re
import unicodedata


def normalize_label(value: str) -> str:
    """Normalize case and whitespace for comparison, never for display."""
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


_UNIT_ALIASES = {
    "g": ("mass", Decimal("1"), "g"),
    "gm": ("mass", Decimal("1"), "g"),
    "gram": ("mass", Decimal("1"), "g"),
    "grams": ("mass", Decimal("1"), "g"),
    "kg": ("mass", Decimal("1000"), "g"),
    "kgs": ("mass", Decimal("1000"), "g"),
    "kilogram": ("mass", Decimal("1000"), "g"),
    "kilograms": ("mass", Decimal("1000"), "g"),
    "mg": ("mass", Decimal("0.001"), "g"),
    "milligram": ("mass", Decimal("0.001"), "g"),
    "milligrams": ("mass", Decimal("0.001"), "g"),
    "ml": ("volume", Decimal("1"), "ml"),
    "milliliter": ("volume", Decimal("1"), "ml"),
    "milliliters": ("volume", Decimal("1"), "ml"),
    "l": ("volume", Decimal("1000"), "ml"),
    "ltr": ("volume", Decimal("1000"), "ml"),
    "liter": ("volume", Decimal("1000"), "ml"),
    "liters": ("volume", Decimal("1000"), "ml"),
    "pc": ("count", Decimal("1"), "pc"),
    "pcs": ("count", Decimal("1"), "pc"),
    "piece": ("count", Decimal("1"), "pc"),
    "pieces": ("count", Decimal("1"), "pc"),
}


def canonical_weight(value, unit: str) -> tuple[Decimal, str]:
    """Convert only known compatible units; unknown units remain separate labels."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Weight must be a valid number")
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Weight must be greater than zero")
    normalized_unit = normalize_label(unit)
    known = _UNIT_ALIASES.get(normalized_unit)
    if known:
        _, multiplier, base = known
        return (amount * multiplier).quantize(Decimal("0.000001")), base
    # Preserve separation for unknown units; case/space normalization only.
    return amount.quantize(Decimal("0.000001")), normalized_unit


def product_identity(name: str, weight, unit: str) -> tuple[str, Decimal, str]:
    normalized_name = normalize_label(name)
    if not normalized_name:
        raise ValueError("Product name cannot be empty")
    amount, canonical_unit = canonical_weight(weight, unit)
    return normalized_name, amount, canonical_unit


def display_name(value: str) -> str:
    """Trim and collapse whitespace while retaining user-facing capitalization."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or "")).strip())
