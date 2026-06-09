# Incident Workflow

## Lifecycle

1. A user selects or creates an incident template from `incidents.json`.
2. The user chooses a GitLab target repository and branch.
3. The backend creates an incident record with target repo, branch, module, and validation strategy metadata.
4. The configured trigger generates runtime logs when a local benchmark target is available.
5. LangGraph executes the incident-response workflow.
6. Evidence is collected from logs, GitLab commits, source files, and CI/CD pipelines.
7. Evidence Fusion produces root cause, confidence, affected file, and evidence chain.
8. Patch Generation proposes a source replacement and unified diff.
9. Validation runs the strategy named by the incident template.
10. MR & RCA creates a branch, commits the patch, opens a GitLab MR, and persists the RCA.
11. Metrics are recomputed and stored in SQLite.

## Dynamic Incident Registry

Incident templates live in `incidents.json`:

```json
{
  "id": "INC-101",
  "module": "currency",
  "validation": "currency_validator",
  "target_file": "currency/converter.py",
  "test_target": "tests/test_currency.py::test_get_rate_pre2024_uses_historical_rate"
}
```

Adding a new scenario usually requires adding a template with:

```text
id
title
description
module
validation
target_file
test_target
supporting_files
priority_signals
```

The API also exposes JSON-backed template operations:

```text
GET    /api/incidents/templates
POST   /api/incidents/templates
DELETE /api/incidents/templates/{ticket_id}
```

## Validation Strategy Pattern

The validation core only delegates:

```text
incident template -> validation strategy -> result
```

Registered strategies:

```text
currency_validator
auth_validator
dependency_validator
generic_pytest
```

The first three are benchmark aliases over the generic pytest strategy. Future incidents can reuse `generic_pytest` by supplying a `test_target` and `supporting_files` in `incidents.json`.

## Metrics

Persisted metrics:

```text
Investigation Time
Evidence Sources Correlated
Files Analyzed
Root Cause Confidence
Validation Success Rate
Patch Success Rate
Merge Requests Created
```

Dashboard summary endpoint:

```text
GET /api/incidents/metrics/summary
```
