"""FastAPI entrypoint for the billing service."""

from fastapi import FastAPI, HTTPException
from typing import List, Optional
from datetime import datetime
from .invoice_service import create_invoice, compute_total
from .tax_engine import get_jurisdiction_rate

app = FastAPI(title="Invoice Billing Service", version="1.3.0")


@app.post("/invoices")
def create_invoice_endpoint(
    invoice_id: str,
    customer_id: str,
    line_items: List[dict],
    currency: str = "USD",
    jurisdiction: str = "US-CA",
    created_at: Optional[datetime] = None,
):
    """Create a new invoice and return its computed total."""
    tax_rate = get_jurisdiction_rate(jurisdiction)
    invoice = create_invoice(
        invoice_id=invoice_id,
        customer_id=customer_id,
        line_items=line_items,
        currency=currency,
        tax_rate=tax_rate,
        created_at=created_at,
    )
    return compute_total(invoice)


@app.get("/invoices/{invoice_id}/total")
def get_invoice_total(invoice_id: str):
    """Stub: fetch and recompute total for a stored invoice."""
    # TODO: wire up DB lookup in Q2
    raise HTTPException(status_code=501, detail="DB lookup not yet implemented")
