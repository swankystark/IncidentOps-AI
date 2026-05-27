"""Invoice creation and total computation service.

Handles the full lifecycle of an invoice: creation, line-item aggregation,
tax application, and final total computation.

Maintained by: platform-team
Last updated: 2023-11-14
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from .tax_engine import calculate_tax


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float  # always in USD
    currency: str = "USD"


class Invoice(BaseModel):
    invoice_id: str
    customer_id: str
    line_items: List[LineItem]
    currency: str = "USD"
    created_at: datetime = None
    tax_rate: float = 0.0
    status: str = "draft"  # draft | issued | paid | void

    def __init__(self, **data):
        if "created_at" not in data or data["created_at"] is None:
            data["created_at"] = datetime.utcnow()
        super().__init__(**data)


def create_invoice(
    invoice_id: str,
    customer_id: str,
    line_items: List[dict],
    currency: str = "USD",
    tax_rate: float = 0.0,
    created_at: Optional[datetime] = None,
) -> Invoice:
    """Create a new invoice with the given line items.

    Args:
        invoice_id: Unique identifier for this invoice.
        customer_id: The customer this invoice belongs to.
        line_items: List of dicts with keys: description, quantity, unit_price.
        currency: Billing currency (default USD).
        tax_rate: Applicable tax rate as a decimal (e.g. 0.08 for 8%).
        created_at: Override creation timestamp (used for backfilling).

    Returns:
        A fully constructed Invoice object.
    """
    items = [LineItem(**item) for item in line_items]
    invoice = Invoice(
        invoice_id=invoice_id,
        customer_id=customer_id,
        line_items=items,
        currency=currency,
        tax_rate=tax_rate,
        created_at=created_at,
    )
    return invoice


def compute_total(invoice: Invoice) -> dict:
    """Compute the subtotal, tax, and grand total for an invoice.

    Returns a breakdown dict with subtotal, tax_amount, and total.
    """
    subtotal = sum(item.quantity * item.unit_price for item in invoice.line_items)
    tax_amount = calculate_tax(subtotal, invoice.tax_rate)
    total = subtotal + tax_amount

    return {
        "invoice_id": invoice.invoice_id,
        "currency": invoice.currency,
        "subtotal": round(subtotal, 2),
        "tax_amount": round(tax_amount, 2),
        "total": round(total, 2),
    }
