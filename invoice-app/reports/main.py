"""FastAPI entrypoint for the reports service."""

from fastapi import FastAPI, Query
from datetime import datetime
from typing import Optional
from .report_service import generate_historical_report, generate_monthly_summary

app = FastAPI(title="Invoice Reports Service", version="1.0.2")


@app.get("/reports/historical")
def historical_report(
    customer_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    """Return a historical invoice report with USD-normalised totals."""
    return generate_historical_report(
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/reports/monthly")
def monthly_summary(
    year: int = Query(..., description="4-digit year, e.g. 2023"),
    month: int = Query(..., ge=1, le=12, description="Month number 1-12"),
):
    """Return a monthly invoice summary with per-currency breakdown."""
    return generate_monthly_summary(year=year, month=month)
