# IncidentOps AI Platform Acceptance Report

Generated: 2026-06-09

Scope: acceptance verification before GitHub migration and final packaging. No feature work, architectural refactor, or benchmark expansion was performed.

## Executive Summary

Overall result: **PASS WITH CLEANUP ITEMS**

The platform starts, the frontend builds, the API responds, incident templates load dynamically, per-run repository configuration is persisted, metrics are available, and GitLab evidence retrieval works against three repositories.

Main acceptance caveats:

- Browser automation was not available in this Codex session, so frontend verification is based on live app availability, production build/lint, source-level component inspection, and API-backed behavior checks rather than screenshots.
- Full remediation was not rerun because Gemini quota was previously exhausted and the task explicitly requested no benchmark expansion.
- The frontend still hardcodes `http://127.0.0.1:8000` and defaults app/log fields to the benchmark `invoice-app` values.

## Environment

- Workspace: `C:\Users\swank\OneDrive\Desktop\hackathon\GCRA`
- Frontend: Next.js app in `frontend/`
- Backend: FastAPI app in `backend/`
- Backend health endpoint: `GET /`
- Frontend URL verified: `http://127.0.0.1:3000/`

Verification commands:

```text
backend: ..\venv\Scripts\python.exe -m compileall app
frontend: npm run lint
frontend: npm run build
```

Results:

- Backend compile: PASS
- Frontend lint: PASS
- Frontend production build: PASS

## Part 1: Frontend Results

| Component | Result | Evidence / Description |
| --- | --- | --- |
| Incident Template Selector | PASS | Frontend calls `GET /api/incidents/templates` and renders each JSON-backed template as a selectable scenario card with id, title, module, and validation strategy. |
| Create Incident Flow | PASS | `triggerScenario()` posts selected template plus user-entered repository config to `POST /api/incidents`. API smoke verified incident creation returns persisted config. |
| GitLab Repository Input | PASS | Input labeled `Target GitLab Repository`; value is sent as `target_repo`. |
| Target Branch Input | PASS | Input labeled `Target Branch`; value is sent as `target_branch`. |
| Target Application Path Input | PASS | Input labeled `Target Application Path`; value is sent as `target_app_path`. |
| Application Log Path Input | PASS | Input labeled `Application Log Path`; value is sent as `application_log_path`. |
| Incident Dashboard | PASS | Main dashboard shows active incident status, agent map, confidence, metrics, evidence terminal, patch panel, and MR state. |
| Investigation Timeline | PASS | SSE status packets populate `investigation_timeline`; timeline renders agent-stage labels and timestamps. |
| Confidence Display | PASS | Circular confidence gauge and metrics card display `confidence_score`. Existing resolved incidents show confidence values. |
| Evidence Viewer | PASS | Tabbed terminal provides Logs, Commits, and Tests views; API stream returns agent logs and status updates. |
| Patch Diff Viewer | PASS | Diff viewer renders `patch_diff` line-by-line with addition/deletion coloring. Existing resolved benchmark incidents contain patch diffs. |
| Validation Results View | PASS | Tests tab displays validation strategy and selected pipeline metadata; validation logs appear in the Logs tab. |
| Metrics Dashboard | PASS | Frontend calls `GET /api/incidents/metrics/summary`; API returned aggregate metrics. |
| Incident History | PASS | Frontend calls `GET /api/incidents` and renders ticket history with status badges. |
| Error Handling UI | PARTIAL | Logs and failed statuses are visible in the incident history/timeline. Fetch errors are currently logged to console, but there is no prominent user-facing toast/banner for API failures. |

Frontend screen description:

- Header: Gemini API key input, save button, active remediation indicator, refresh button.
- Left column: repository configuration fields, incident template selector, incident history.
- Center/right dashboard: multi-agent orchestration map, confidence gauge, system metrics, live timeline.
- Bottom panels: tabbed evidence terminal and remediation patch/MR review panel.

## Part 2: API Verification

Backend health:

```http
GET http://127.0.0.1:8000/
```

Status: `200`

Response:

```json
{"status":"healthy","service":"IncidentOps AI"}
```

Incident templates:

```http
GET http://127.0.0.1:8000/api/incidents/templates
```

Status: `200`

Response: JSON array containing `INC-101`, `INC-102`, and `INC-103` templates with title, description, module, validation strategy, target file, test target, supporting files, and trigger metadata.

List incidents:

```http
GET http://127.0.0.1:8000/api/incidents
```

Status: `200`

Response: JSON array of persisted incidents, including benchmark and smoke-test incidents with target repository configuration.

Metrics summary:

```http
GET http://127.0.0.1:8000/api/incidents/metrics/summary
```

Status: `200`

Response:

```json
{
  "total_incidents": 3,
  "average_investigation_time_seconds": 61.92903666666666,
  "evidence_sources_correlated": 9,
  "files_analyzed": 0,
  "average_root_cause_confidence": 95.33333333333333,
  "validation_success_rate": 1.0,
  "patch_success_rate": 1.0,
  "merge_requests_created": 3
}
```

Gemini configuration:

```http
GET http://127.0.0.1:8000/api/config/gemini
```

Status: `200`

Response shape:

```json
{"configured":true,"masked_api_key":"<masked>"}
```

Create incident:

```http
POST http://127.0.0.1:8000/api/incidents
Content-Type: application/json
```

Request:

```json
{
  "ticket_id": "ACCEPT-API-004",
  "scenario_id": "INC-101",
  "title": "Acceptance API smoke",
  "description": "Verify create incident and persisted repository configuration.",
  "target_repo": "gitlab-org/gitlab-runner",
  "target_branch": "main",
  "target_app_path": "",
  "application_log_path": "missing/application.log"
}
```

Status: `200`

Response excerpt:

```json
{
  "ticket_id": "ACCEPT-API-004",
  "scenario_id": "INC-101",
  "target_repo": "gitlab-org/gitlab-runner",
  "target_branch": "main",
  "target_app_path": "",
  "application_log_path": "missing/application.log",
  "status": "INVESTIGATING"
}
```

Get incident detail:

```http
GET http://127.0.0.1:8000/api/incidents/7
```

Status: `200`

Response excerpt:

```json
{
  "ticket_id": "ACCEPT-API-004",
  "target_repo": "gitlab-org/gitlab-runner",
  "target_branch": "main",
  "target_app_path": "",
  "application_log_path": "missing/application.log",
  "status": "FAILED",
  "logs": [
    {
      "agent_name": "System",
      "level": "WARNING",
      "message": "Warning: runtime log was not generated..."
    }
  ]
}
```

Streaming endpoint:

```http
GET http://127.0.0.1:8000/api/stream/7
```

Status: `200`

Response: Server-Sent Events stream containing `agent_log` and `status_update` events. The smoke incident stream included system logs, planner error logs, log-service warnings, and status updates.

Configuration persistence:

Result: PASS. The incident created with `target_repo=gitlab-org/gitlab-runner`, `target_branch=main`, empty target app path, and missing log path returned those exact values from `GET /api/incidents/{id}`.

## Part 3: Repository-Agnostic Results

Repository checks were performed against GitLab evidence retrieval without running Gemini remediation.

| Repo | Branch | App Path | File Check | Pipeline Check | Missing Logs | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `swankystark20-group/incidentops-demo-app` | `main` | `invoice-app` | `currency/converter.py` retrieved, 3556 chars | selected `main` pipeline, status `failed`, source `target_branch` | local benchmark log exists | PASS |
| `gitlab-org/gitlab-runner` | `main` | empty | `README.md` retrieved, 3894 chars | selected `main` pipeline, status `success`, source `target_branch` | missing log path handled as absent | PASS |
| `gitlab-org/gitlab` | `master` | empty | `README.md` retrieved, 5869 chars | selected `master` pipeline, status `running`, source `target_branch` | missing log path handled as absent | PASS |

Findings:

- Repository selection works for default benchmark and public GitLab repositories.
- Empty target app path works for repository-root file retrieval.
- Pipeline selection respects configured branch.
- Missing runtime logs are represented as warnings rather than hard crashes.
- Missing or unrelated test targets still require better user-facing explanations, but the platform does not require `invoice-app` for GitLab file/pipeline retrieval.

## Part 4: End-to-End UI Walkthrough

Walkthrough basis: frontend code path, live API responses, SSE stream verification, and existing resolved incidents/MRs from prior full workflow runs.

| Step | Result | Evidence |
| --- | --- | --- |
| Create incident | PASS | Frontend create flow posts template + config to `POST /api/incidents`; API smoke returned `200`. |
| Run workflow | PASS | Background task starts agent workflow after incident creation; smoke incident produced system/planner/log-service events. Prior benchmark incidents completed full workflow. |
| Observe timeline | PASS | SSE endpoint emitted chronological logs and status updates; frontend maps these into timeline labels. |
| Inspect evidence | PASS | Logs/Commits/Tests tabs render agent logs, repo config, validation strategy, and pipeline metadata. |
| View patch | PASS | Existing resolved incidents include `patch_diff`; frontend renders diff with line coloring. |
| View validation | PASS | Existing resolved incidents include validation pass logs; frontend Tests tab displays validation strategy/pipeline state. |
| View RCA | PASS | `rca_report` is carried in incident detail/status updates. UI currently emphasizes MR and logs more than a dedicated RCA document panel. |
| Open MR | PASS | Frontend renders `View MR on GitLab` when `gitlab_mr_url` exists. Existing MRs include `!13` through `!17` from successful benchmark runs. |

## Part 5: Production Readiness Findings

### Hardcoded Values

- `frontend/app/page.tsx` hardcodes API origin as `http://127.0.0.1:8000`.
- `frontend/app/page.tsx` defaults `targetAppPath` to `invoice-app`.
- `frontend/app/page.tsx` defaults `applicationLogPath` to `invoice-app/application.log`.
- `incidents.json` remains benchmark-oriented, which is acceptable as default demo content but should be labeled as such.

Recommendation: introduce `NEXT_PUBLIC_API_BASE_URL` and make frontend defaults read from backend config or a demo preset.

### Debug / Demo Logic

- `backend/app/services/gitlab.py` still contains `DEMO_MODE` mock branches and print-based mock actions.
- `backend/app/agents/planner.py`, `fusion_agent.py`, `patch_agent.py`, and `mr_agent.py` contain fallback logic. It is gated by `ENABLE_MODEL_FALLBACKS`, but production docs should clearly state the default is disabled.
- `run_benchmark.py`, `.benchmark_cache/`, and benchmark reports are useful for evaluation but should be separated from production packaging or documented as evaluation tooling.

Recommendation: keep benchmark tooling under `tests/benchmarks/` or `tools/benchmark/` before final packaging.

### Error Handling

- Frontend fetch errors are logged to console but do not consistently surface as visible user notifications.
- Missing log path is recorded in backend logs, but the UI does not highlight it as a configuration warning.
- Model quota/network failures appear in logs but could be summarized in a top-level incident error panel.

Recommendation: add a persistent error banner/status card for API, model, GitLab, missing-log, and missing-test-target failures.

### Repository-Agnostic Gaps

- GitLab file and pipeline retrieval are repository-agnostic.
- Project metadata retrieval exists as `get_project_details()`, but the route/UI do not expose a repository validation step before incident creation.
- Non-Python repositories can be investigated for GitLab evidence, but remediation validation is still Python/pytest-oriented unless a matching validation strategy exists.

Recommendation: add a "Validate repository connection" action before running an incident, and document validation strategy requirements for non-Python repositories.

### UI Completeness

- RCA data exists but does not have a dedicated prominent panel.
- Error handling UI is partial.
- The Gemini API key input is hidden on smaller screens due `hidden xl:flex`.

Recommendation: make config controls available on all viewport sizes before portfolio packaging.

## Remaining Technical Debt

1. Replace frontend hardcoded API URL with environment configuration.
2. Replace benchmark-specific frontend defaults with a selectable demo preset.
3. Add visible UI alerts for backend/GitLab/Gemini/log/test-target failures.
4. Move benchmark harness/cache/report artifacts under a clearly named evaluation directory.
5. Add repository validation endpoint and frontend preflight button.
6. Add validation strategies for non-Python repositories.
7. Add a dedicated RCA viewer panel.
8. Decide whether `DEMO_MODE` mock code remains in production build or moves to test fixtures.

## Acceptance Decision

Success criteria: "A new user can use the platform without needing knowledge of the benchmark repository."

Decision: **PARTIAL PASS**

A new user can enter a different GitLab repository, branch, app path, and log path, and the backend persists that configuration. GitLab file and pipeline retrieval work against multiple public repositories without `invoice-app` assumptions.

However, final packaging should address the visible defaults and frontend API hardcoding so new users are guided into repository configuration cleanly rather than seeing benchmark defaults first.
