# invoice-app

Internal financial SaaS platform for invoice management, multi-currency billing, and reporting.

## Overview

This service handles:
- Invoice creation and tax computation
- Multi-currency support with historical exchange rates
- Monthly and historical reporting
- User authentication and session management

## Architecture

```
invoice-app/
├── billing/          # Invoice creation, tax engine, totals
├── currency/         # FX conversion, historical rates
├── reports/          # Reporting endpoints, monthly summaries
├── auth/             # Login, session, token validation
└── tests/            # Unit + integration tests
```

## Getting Started

```bash
pip install -r requirements.txt
uvicorn billing.main:app --reload
```

## Running Tests

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | JWT signing secret | `dev-secret` |
| `FX_API_URL` | Exchange rate API base URL | `https://api.exchangerate.host` |
| `DB_URL` | Database connection string | `sqlite:///./invoice.db` |

## Notes

- Historical reports use archived exchange rates for pre-2024 invoices
- All monetary values stored in USD internally, converted on output
- Sessions expire after 3600 seconds by default

## Maintainers

- Platform Team (`@platform-team`)
- Last major refactor: 2023-11 (currency module rewrite)
