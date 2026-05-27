"""Tax calculation engine.

Supports flat-rate and tiered tax computation.
Integrates with pydantic for config validation.

NOTE: This module was updated during the pydantic v1 -> v2 migration sprint.
Some validators may behave differently depending on installed pydantic version.
See: https://docs.pydantic.dev/latest/migration/

Maintained by: platform-team
Last updated: 2023-12-01
"""

# BUG #3 (Dependency Mismatch): requirements.txt pins pydantic==1.9.0 but this
# module uses pydantic v2-style model_validator syntax. Under pydantic 1.9.0,
# `model_validator` does not exist, causing an ImportError at runtime.
# The CI lint stage passes because flake8 doesn't resolve imports,
# but the test stage fails when the module is actually loaded.
from pydantic import BaseModel, model_validator  # noqa: F401 -- fails on pydantic <2.0


class TaxConfig(BaseModel):
    """Tax configuration for a given jurisdiction."""

    jurisdiction: str
    rate: float  # e.g. 0.08 for 8%
    applies_to: str = "all"  # all | goods | services

    @model_validator(mode="after")  # pydantic v2 syntax -- breaks on v1.9.0
    def validate_rate(self):
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(f"Tax rate must be between 0 and 1, got {self.rate}")
        return self


def calculate_tax(subtotal: float, rate: float) -> float:
    """Apply a flat tax rate to a subtotal.

    Args:
        subtotal: Pre-tax amount in the invoice currency.
        rate: Tax rate as a decimal fraction (0.0 - 1.0).

    Returns:
        Tax amount to be added to the subtotal.
    """
    if rate < 0 or rate > 1:
        raise ValueError(f"Invalid tax rate: {rate}. Must be between 0.0 and 1.0.")
    return round(subtotal * rate, 2)


def get_jurisdiction_rate(jurisdiction: str) -> float:
    """Return the default tax rate for a known jurisdiction.

    Falls back to 0.0 for unknown jurisdictions (tax-exempt assumed).
    """
    # Hardcoded for now; will be replaced by DB lookup in Q2
    RATES = {
        "US-CA": 0.0875,
        "US-NY": 0.08,
        "US-TX": 0.0625,
        "EU-DE": 0.19,
        "EU-FR": 0.20,
        "GB": 0.20,
    }
    return RATES.get(jurisdiction, 0.0)
