"""Unit tests for the billing module.

Covers invoice creation, tax calculation, and total computation.
All tests use in-memory fixtures -- no external dependencies required.
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Tax engine tests
# ---------------------------------------------------------------------------

def test_calculate_tax_standard():
    """Basic tax calculation at 8% rate."""
    from billing.tax_engine import calculate_tax
    assert calculate_tax(1000.0, 0.08) == 80.0


def test_calculate_tax_zero_rate():
    from billing.tax_engine import calculate_tax
    assert calculate_tax(500.0, 0.0) == 0.0


def test_calculate_tax_invalid_rate():
    from billing.tax_engine import calculate_tax
    with pytest.raises(ValueError):
        calculate_tax(100.0, 1.5)


def test_get_jurisdiction_rate_known():
    from billing.tax_engine import get_jurisdiction_rate
    assert get_jurisdiction_rate("US-CA") == 0.0875
    assert get_jurisdiction_rate("EU-DE") == 0.19


def test_get_jurisdiction_rate_unknown():
    from billing.tax_engine import get_jurisdiction_rate
    assert get_jurisdiction_rate("ZZ-XX") == 0.0


# ---------------------------------------------------------------------------
# BUG #3 -- This test fails because pydantic==1.9.0 does not support
# `model_validator`, causing an ImportError when tax_engine is loaded.
# The test is intentionally left here to surface the dependency mismatch
# in CI. Fix: upgrade pydantic to >=2.0 in requirements.txt.
# ---------------------------------------------------------------------------

def test_tax_config_model_valid():
    """FAILING TEST (Bug #3): TaxConfig uses pydantic v2 model_validator.

    Fails with: ImportError: cannot import name 'model_validator' from 'pydantic'
    when pydantic==1.9.0 is installed.
    """
    from billing.tax_engine import TaxConfig  # ImportError on pydantic <2.0
    config = TaxConfig(jurisdiction="US-CA", rate=0.0875)
    assert config.rate == 0.0875


def test_tax_config_model_invalid_rate():
    """FAILING TEST (Bug #3): Same import failure as above."""
    from billing.tax_engine import TaxConfig
    with pytest.raises(ValueError):
        TaxConfig(jurisdiction="US-CA", rate=1.5)


# ---------------------------------------------------------------------------
# Invoice service tests
# ---------------------------------------------------------------------------

def test_create_invoice_basic():
    from billing.invoice_service import create_invoice
    inv = create_invoice(
        invoice_id="INV-TEST-001",
        customer_id="cust-1",
        line_items=[
            {"description": "Consulting", "quantity": 2, "unit_price": 500.0},
        ],
        currency="USD",
        tax_rate=0.08,
    )
    assert inv.invoice_id == "INV-TEST-001"
    assert len(inv.line_items) == 1


def test_compute_total_no_tax():
    from billing.invoice_service import create_invoice, compute_total
    inv = create_invoice(
        invoice_id="INV-TEST-002",
        customer_id="cust-2",
        line_items=[
            {"description": "License", "quantity": 1, "unit_price": 1200.0},
            {"description": "Support", "quantity": 12, "unit_price": 50.0},
        ],
        tax_rate=0.0,
    )
    result = compute_total(inv)
    assert result["subtotal"] == 1800.0
    assert result["tax_amount"] == 0.0
    assert result["total"] == 1800.0


def test_compute_total_with_tax():
    from billing.invoice_service import create_invoice, compute_total
    inv = create_invoice(
        invoice_id="INV-TEST-003",
        customer_id="cust-3",
        line_items=[
            {"description": "Service", "quantity": 1, "unit_price": 1000.0},
        ],
        tax_rate=0.10,
    )
    result = compute_total(inv)
    assert result["subtotal"] == 1000.0
    assert result["tax_amount"] == 100.0
    assert result["total"] == 1100.0
