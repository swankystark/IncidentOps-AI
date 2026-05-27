"""FastAPI entrypoint for the currency service."""

from fastapi import FastAPI, Query
from datetime import datetime
from typing import Optional
from .converter import convert_currency, get_rate

app = FastAPI(title="Currency Conversion Service", version="1.1.0")


@app.get("/convert")
def convert(
    amount: float,
    from_currency: str,
    to_currency: str,
    as_of: Optional[datetime] = Query(default=None),
):
    """Convert an amount between two currencies.

    Pass `as_of` to use historical rates (pre-2024 invoices).
    """
    result = convert_currency(amount, from_currency, to_currency, as_of=as_of)
    return {
        "amount": amount,
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "converted": result,
        "as_of": as_of.isoformat() if as_of else "live",
    }


@app.get("/rates/{currency}")
def get_current_rate(currency: str, as_of: Optional[datetime] = Query(default=None)):
    """Return the current or historical USD rate for a currency."""
    rate = get_rate(currency, as_of=as_of)
    return {"currency": currency.upper(), "rate_vs_usd": rate, "as_of": as_of or "live"}
