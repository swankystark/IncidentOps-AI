"""Unit tests for the currency module.

Includes tests for live rate lookup, historical rate resolution,
and currency conversion. Bug #1 is demonstrated via a failing test
that checks pre-2024 invoice conversion against known historical rates.
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Historical rate tests
# ---------------------------------------------------------------------------

def test_get_historical_rate_known_month():
    """Historical rate for a known snapshot month should return archived value."""
    from currency.historical import get_historical_rate
    rate = get_historical_rate("EUR", as_of=datetime(2023, 3, 15))
    assert rate == 1.08  # from 2023-03 snapshot


def test_get_historical_rate_fallback():
    """Missing month should fall back to nearest available snapshot."""
    from currency.historical import get_historical_rate
    # 2023-04 has no snapshot; should fall back to 2023-03
    rate = get_historical_rate("EUR", as_of=datetime(2023, 4, 10))
    assert rate == 1.08


def test_get_historical_rate_unknown_currency():
    from currency.historical import get_historical_rate
    rate = get_historical_rate("XYZ", as_of=datetime(2023, 6, 1))
    assert rate == 1.0  # default parity


# ---------------------------------------------------------------------------
# Converter tests -- live rates
# ---------------------------------------------------------------------------

def test_get_rate_live_eur():
    from currency.converter import get_rate
    rate = get_rate("EUR")  # no as_of -> live
    assert rate == 0.92


def test_convert_currency_same_currency():
    from currency.converter import convert_currency
    result = convert_currency(100.0, "USD", "USD")
    assert result == 100.0


def test_convert_currency_usd_to_eur():
    from currency.converter import convert_currency
    # 100 USD -> EUR at live rate 0.92
    result = convert_currency(100.0, "USD", "EUR")
    assert result == 92.0


# ---------------------------------------------------------------------------
# BUG #1 -- Failing test demonstrating currency conversion regression
#
# Pre-2024 invoices should use historical rates from the snapshot archive.
# As of the 2023-11 refactor, get_rate() silently falls through to live
# rates for all pre-2024 dates, producing incorrect USD-normalised totals.
#
# Example discrepancy:
#   INV-001: 1200 EUR, created 2023-03-15
#   Historical rate (2023-03): 1 EUR = 1.08 USD  -> correct USD = 1296.00
#   Live rate (current):       1 EUR = 0.92 USD  -> wrong   USD = 1304.35
#   Discrepancy: ~$8.35 per invoice (compounds across thousands of records)
# ---------------------------------------------------------------------------

def test_get_rate_pre2024_uses_historical_rate():
    """FAILING TEST (Bug #1): Pre-2024 rate lookup should return historical value.

    get_rate('EUR', as_of=datetime(2023, 3, 15)) should return 1.08 (archived).
    Instead returns 0.92 (live rate) due to missing historical branch in converter.py.
    """
    from currency.converter import get_rate
    rate = get_rate("EUR", as_of=datetime(2023, 3, 15))
    # Expect historical rate from 2023-03 snapshot
    assert rate == 1.08, (
        f"Expected historical rate 1.08 for EUR in 2023-03, got {rate}. "
        "Likely caused by live rate cache fallthrough in converter.get_rate()."
    )


def test_historical_report_usd_normalisation_pre2024():
    """FAILING TEST (Bug #1): Historical report totals are wrong for pre-2024 invoices.

    INV-001 (1200 EUR, 2023-03) should normalise to 1296.00 USD at historical rate.
    Due to Bug #1, it normalises to 1304.35 USD using the live rate instead.
    """
    from reports.report_service import generate_historical_report
    report = generate_historical_report(
        customer_id="cust-42",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
    )
    # INV-001: 1200 EUR / 1.08 (historical) = 1111.11 USD
    inv = next(i for i in report["invoices"] if i["invoice_id"] == "INV-001")
    assert abs(inv["usd_equivalent"] - 1111.11) < 0.10, (
        f"Expected ~1111.11 USD for INV-001 using historical rate, "
        f"got {inv['usd_equivalent']}. Bug #1: live rate used instead of historical."
    )
