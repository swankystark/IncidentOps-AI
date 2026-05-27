"""Historical exchange rate archive.

Provides point-in-time exchange rates for archived invoice processing.
Rates are sourced from our internal FX snapshot store (S3-backed).

This module is used exclusively for pre-2024 invoice reconciliation.
For live rates, see converter.py.

Maintained by: platform-team
Last updated: 2023-10-05
"""

from datetime import datetime
from typing import Optional

# Archived monthly average rates (USD base) for pre-2024 periods.
# Source: internal FX snapshot store, reconciled against ECB reference rates.
# Format: { "YYYY-MM": { "CURRENCY": rate } }
_HISTORICAL_RATES: dict = {
    "2023-01": {"EUR": 1.07, "GBP": 1.23, "JPY": 130.5, "CAD": 1.34, "AUD": 1.47},
    "2023-02": {"EUR": 1.06, "GBP": 1.21, "JPY": 132.1, "CAD": 1.35, "AUD": 1.49},
    "2023-03": {"EUR": 1.08, "GBP": 1.24, "JPY": 131.8, "CAD": 1.36, "AUD": 1.50},
    "2023-06": {"EUR": 1.09, "GBP": 1.27, "JPY": 141.0, "CAD": 1.32, "AUD": 1.51},
    "2023-09": {"EUR": 1.06, "GBP": 1.25, "JPY": 147.8, "CAD": 1.36, "AUD": 1.55},
    "2023-12": {"EUR": 1.10, "GBP": 1.27, "JPY": 141.9, "CAD": 1.33, "AUD": 1.53},
}


def get_historical_rate(currency: str, as_of: Optional[datetime] = None) -> float:
    """Return the archived USD exchange rate for a currency at a given date.

    Looks up the closest available monthly snapshot. Falls back to 1.0
    (USD parity) if no snapshot is found for the requested period.

    Args:
        currency: Currency code (e.g. 'EUR').
        as_of: The date for which to retrieve the historical rate.

    Returns:
        Exchange rate as float (units of `currency` per 1 USD).
    """
    if as_of is None:
        # No date context -- return neutral rate
        return 1.0

    month_key = as_of.strftime("%Y-%m")
    snapshot = _HISTORICAL_RATES.get(month_key)

    if snapshot is None:
        # No exact snapshot: walk backwards up to 3 months to find nearest
        for delta in range(1, 4):
            fallback_month = (as_of.month - delta)
            fallback_year = as_of.year
            if fallback_month <= 0:
                fallback_month += 12
                fallback_year -= 1
            key = f"{fallback_year}-{fallback_month:02d}"
            snapshot = _HISTORICAL_RATES.get(key)
            if snapshot:
                break

    if snapshot is None:
        return 1.0  # Unknown period, default to USD parity

    return snapshot.get(currency.upper(), 1.0)
