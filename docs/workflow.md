# IncidentOps AI Workflow

This file describes the operator-visible flow and the backend recovery path.

## End-to-End Lifecycle

1. Select or create an incident template from `incidents.json`.
2. Enter the target GitLab repository, branch, application path, and log path.
3. Click validate to confirm the repository is reachable.
4. Trigger the incident.
5. Watch the SSE stream and agent logs while the LangGraph workflow runs.
6. Review the RCA, patch diff, validation result, and MR link.
7. Approve or continue investigation from the human review gate.

## Backend Phases

### 1. Planner
- Scopes the incident from the title, description, and template.
- Seeds retrieval signals for the log and GitLab branches.

### 2. Retrieval
- `log_service` extracts runtime evidence from the configured log path.
- `gitlab_service` finds commits, file contents, and a pinned commit SHA.
- `cicd_service` uses that pinned SHA to fetch pipeline and job evidence.

### 3. Evidence Fusion
- Correlates the evidence streams into a root-cause hypothesis.
- Chooses the most likely `affected_file`.

### 4. Repository Context
- Expands the file into related files, imports, tests, and recent commits.
- Uses static analysis and GitLab data only.

### 5. Patch Targeting
- Narrows the edit region to the exact function or block.
- Produces the context needed for patch generation.

### 6. Patch Generation
- Emits a minimal source diff.
- Fails fast if the affected source cannot be read.

### 7. Validation
- Runs the template-selected validation strategy.
- Retries patch generation once on validation failure.

### 8. MR + RCA
- Creates the remediation branch.
- Commits the fix.
- Opens the MR and posts the RCA as a note.

## Validation Strategy Pattern

```text
incident_template.validation -> ValidationStrategy -> result
```

Registered strategies:
- `currency_validator`
- `auth_validator`
- `dependency_validator`
- `generic_pytest`

## Incident Template Fields

- `id`
- `title`
- `description`
- `module`
- `validation`
- `target_file`
- `test_target`
- `supporting_files`
- `priority_signals`
- `trigger`

## Operator Checks

1. Repository validate returns `ok: true`.
2. Logs show planner, retrieval, fusion, context, patch, validation, and MR stages.
3. `validation_passed` is true before the MR stage when possible.
4. The incident ends with `gitlab_mr_url` and `rca_report`.

## Recovery

If a run is interrupted by quota or rate-limit errors:

1. The incident is checkpointed in SQLite.
2. The status becomes `WAITING_FOR_RETRY`.
3. Resume with `POST /api/incidents/{incident_id}/resume`.
4. The saved `checkpoint_state` is loaded and the graph continues from the last known step.
