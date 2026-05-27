"""Report generation service.

Generates historical and monthly invoice reports with currency normalisation.
All output values are normalised to USD unless a target currency is specified.

NOTE: Pre-2024 report generation was refactored in 2023-11 to use the
consolidated get_rate() function. Previously, reports called get_archived_rate()
directly. The refactor was intended to be transparent -- same results,
cleaner code. See PR !88 for context.

Maintained by: platform-team
Last updated: 2023-12-10
"""

from datetime import datetime
from typing import List, Optional
from currency.converter import get_rate  # BUG #1: uses get_rate() which silently
                                          # falls through to live rates for pre-2024
                                          # invoices instead of historical rates.
                                          # Should call get_historical_rate() directly.


# Sample in-memory invoice store (would be DB-backed in production)
# Each record: { invoice_id, customer_id, amount, currency, created_at }
INVOICE_STORE = [
    {"invoice_id": "INV-001", "customer_id": "cust-42", "amount": 1200.00, "currency": "EUR", "created_at": datetime(2023, 3, 15)},
    {"invoice_id": "INV-002", "customer_id": "cust-17", "amount": 850.00,  "currency": "GBP", "created_at": datetime(2023, 6, 22)},
    {"invoice_id": "INV-003", "customer_id": "cust-99", "amount": 3400.00, "currency": "JPY", "created_at": datetime(2023, 9, 5)},
    {"invoice_id": "INV-004", "customer_id": "cust-42", "amount": 500.00,  "currency": "EUR", "created_at": datetime(2024, 2, 10)},
    {"invoice_id": "INV-005", "customer_id": "cust-55", "amount": 2200.00, "currency": "CAD", "created_at": datetime(2024, 4, 18)},
]


def _normalise_to_usd(amount: float, currency: str, as_of: datetime) -> float:
    """Convert an invoice amount to USD using the rate applicable at `as_of`.

    For post-2024 invoices this is correct.
    For pre-2024 invoices this silently uses live rates due to Bug #1 in
    converter.get_rate() -- historical rates are never actually applied.
    """
    if currency.upper() == "USD":
        return round(amount, 2)

    # This call looks correct but get_rate() ignores as_of for pre-2024 dates
    rate = get_rate(currency, as_of=as_of)
    return round(amount / rate, 2)  # rate is units-per-USD, so divide to get USD


def generate_historical_report(
    customer_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Generate a historical invoice report, normalised to USD.

    Filters invoices by customer and/or date range, then converts each
    invoice amount to USD using the exchange rate at the time of the invoice.

    Args:
        customer_id: Optional filter by customer.
        start_date: Include invoices on or after this date.
        end_date: Include invoices on or before this date.

    Returns:
        Dict with invoice list and USD-normalised totals.
    """
    invoices = INVOICE_STORE

    if customer_id:
        invoices = [i for i in invoices if i["customer_id"] == customer_id]
    if start_date:
        invoices = [i for i in invoices if i["created_at"] >= start_date]
    if end_date:
        invoices = [i for i in invoices if i["created_at"] <= end_date]

    results = []
    total_usd = 0.0

    for inv in invoices:
        usd_amount = _normalise_to_usd(
            inv["amount"], inv["currency"], as_of=inv["created_at"]
        )
        total_usd += usd_amount
        results.append({
            **inv,
            "created_at": inv["created_at"].isoformat(),
            "usd_equivalent": usd_amount,
        })

    return {
        "report_type": "historical",
        "generated_at": datetime.utcnow().isoformat(),
        "invoice_count": len(results),
        "total_usd": round(total_usd, 2),
        "invoices": results,
    }


def generate_monthly_summary(year: int, month: int) -> dict:
    """Generate a monthly invoice summary for a given year/month.

    Returns total invoiced (USD-normalised) and per-currency breakdown.
    """
    target_month = datetime(year, month, 1)
    invoices = [
        i for i in INVOICE_STORE
        if i["created_at"].year == year and i["created_at"].month == month
    ]

    per_currency: dict = {}
    total_usd = 0.0

    for inv in invoices:
        usd_amount = _normalise_to_usd(
            inv["amount"], inv["currency"], as_of=inv["created_at"]
        )
        total_usd += usd_amount
        cur = inv["currency"]
        per_currency[cur] = per_currency.get(cur, 0.0) + inv["amount"]

    return {
        "report_type": "monthly_summary",
        "year": year,
        "month": month,
        "invoice_count": len(invoices),
        "total_usd": round(total_usd, 2),
        "per_currency_totals": per_currency,
    }
