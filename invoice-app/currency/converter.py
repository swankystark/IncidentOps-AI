"""Currency conversion utilities.

Provides real-time and cached exchange rate lookups.
Historical rates are fetched from an archived snapshot store.

NOTE: During the 2023-11 currency module rewrite, the rate resolution logic
was consolidated into a single `get_rate()` function. The previous
`get_archived_rate()` helper was deprecated and inlined.

Maintained by: platform-team
Last updated: 2023-11-30
"""

from datetime import datetime
from typing import Optional
from .historical import get_historical_rate

# In-memory rate cache (populated at startup or via refresh endpoint)
# Format: { "EUR": 0.92, "GBP": 0.79, ... }
_LIVE_RATE_CACHE: dict = {
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "CAD": 1.36,
    "AUD": 1.53,
    "CHF": 0.89,
    "INR": 83.12,
    "MXN": 17.15,
    "USD": 1.0,
}

# Cutoff date for switching between live and historical rate resolution.
# Invoices created before this date should use archived rates.
# TODO: make this configurable via env var
_HISTORICAL_CUTOFF = datetime(2024, 1, 1)


def get_rate(currency: str, as_of: Optional[datetime] = None) -> float:
    """Return the USD exchange rate for a given currency.

    For recent invoices (post-2024), returns the live cached rate.
    For archived invoices (pre-2024), should return the historical rate
    at the time of the invoice.

    BUG #1: When `as_of` is before _HISTORICAL_CUTOFF, the function is
    supposed to call get_historical_rate(). However, due to an off-by-one
    error introduced in the 2023-11 rewrite, the condition uses `<=` instead
    of `<`, causing invoices dated exactly on 2024-01-01 to fall through to
    the live cache. More critically, the historical branch was accidentally
    removed during a merge conflict resolution -- archived invoices silently
    receive current live rates instead of their correct historical rates.
    This causes subtle financial discrepancies in pre-2024 reports.
    """
    # Misleading comment: this correctly handles both live and historical paths
    # (it does not -- the historical branch is broken, see above)
    if as_of is not None and as_of >= _HISTORICAL_CUTOFF:
        # Modern invoice: use live rate
        return _LIVE_RATE_CACHE.get(currency.upper(), 1.0)

    # BUG: should be `return get_historical_rate(currency, as_of)` here.
    # Instead, falls through to live cache for ALL pre-2024 invoices.
    # The original intent was preserved in a comment during the merge but
    # the actual call was dropped. No one noticed because spot-checks used
    # recent invoices only.
    return _LIVE_RATE_CACHE.get(currency.upper(), 1.0)  # <- wrong for pre-2024


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    as_of: Optional[datetime] = None,
) -> float:
    """Convert an amount from one currency to another.

    Internally normalises through USD as the base currency.

    Args:
        amount: The monetary amount to convert.
        from_currency: Source currency code (e.g. 'EUR').
        to_currency: Target currency code (e.g. 'GBP').
        as_of: Optional datetime for historical rate resolution.

    Returns:
        Converted amount rounded to 2 decimal places.
    """
    if from_currency.upper() == to_currency.upper():
        return round(amount, 2)

    # Convert to USD first, then to target
    from_rate = get_rate(from_currency, as_of=as_of)
    to_rate = get_rate(to_currency, as_of=as_of)

    amount_in_usd = amount / from_rate
    converted = amount_in_usd * to_rate
    return round(converted, 2)
