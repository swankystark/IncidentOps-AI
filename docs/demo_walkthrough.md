# IncidentOps AI — Demo Walkthrough

This walkthrough demonstrates the full incident-response lifecycle using the benchmark GitLab repository. A new evaluator can follow these steps without prior knowledge of the demo application.

**Benchmark repository:** `swankystark20-group/incidentops-demo-app` (GitLab)  
**Platform repository:** [github.com/swankystark/IncidentOps-AI](https://github.com/swankystark/IncidentOps-AI)

---

## Prerequisites

1. Clone IncidentOps AI and configure `.env` (see [README](../README.md))
2. Start backend on port 8000 and frontend on port 3000
3. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env.local`
4. Have a valid Gemini API key and GitLab PAT

---

## Step 1: Incident Creation

1. Open the dashboard at `http://localhost:3000`
2. Enter your Gemini API key in the header (or configure via `.env`)
3. Click **Apply Demo Preset** — this loads demo values only:
   - Repository: `swankystark20-group/incidentops-demo-app`
   - Branch: `main`
   - App path: `invoice-app`
   - Log path: `invoice-app/application.log`
4. Click **Validate Repository**
   - **PASS** — repository and branch are accessible via GitLab API
   - **FAIL** — fix PAT, repo path, or branch before continuing
5. Select **INC-101** (currency regression) and click to trigger

**What happens:** The backend creates an incident record, logs the planner scope, and starts the LangGraph workflow in the background.

---

## Step 2: Evidence Retrieval

Watch the **Multi-Agent Orchestration Map** as the workflow advances through the retrieval path:

| Service | Evidence Collected |
|---------|-------------------|
| **GitLab Service** | Commit history, suspicious commits, source files |
| **CI/CD Service** | Pipeline status, job traces, test failure output |
| **Log Service** | Runtime error lines from the configured log path |

The **Investigation Terminal** streams agent logs in real time via SSE.

**What to look for:**
- GitLab Service pins a commit SHA for correlation
- CI/CD Service follows the pinned GitLab commit to select the relevant pipeline
- Log Service extracts stack traces and error keywords
- In the final graph, CI/CD runs after GitLab evidence is available, and the fusion step waits for log + CI/CD evidence.

---

## Step 3: Root Cause Analysis

After evidence fusion completes, the **Root Cause Analysis** panel populates:

| Field | Example (INC-101) |
|-------|-----------------|
| Root Cause | Pre-2024 currency conversion uses live rates instead of historical archive |
| Evidence Sources | Commit correlation, test failure, log anomaly |
| Affected Files | `currency/converter.py` |
| Selected Commit | Pinned SHA from GitLab evidence |
| Confidence | ~98% |
| Remediation Summary | Patch strategy for the affected converter logic |

The **Diagnosis Confidence** gauge updates as fusion completes.

---

## Step 4: Patch Generation

The **Remediation Patch** panel shows a unified diff:

- Lines prefixed with `-` are removed
- Lines prefixed with `+` are added
- The patch targets the minimal change needed to fix the root cause

If patch generation fails, an error alert appears in the banner area (e.g., Gemini quota, missing source file).

---

## Step 5: Validation

The **Validation Service** runs the strategy defined in `incidents.json`:

- INC-101 → `currency_validator` (pytest on currency tests)
- INC-102 → `auth_validator`
- INC-103 → `dependency_validator`

**Success:** Validation log shows `PASSED`; workflow advances to MR creation.  
**Failure:** Red alert banner: "Validation failed" with log details.

---

## Step 6: Merge Request Creation

The **MR & RCA Agent**:

1. Generates a full markdown RCA report
2. Creates a GitLab branch (`incidentops/fix-inc-101-...`)
3. Commits the validated patch
4. Opens a merge request with RCA attached

**Review gate:** Once status reaches `RESOLVING`, the **Approve & Merge** button unlocks.

Click **View MR on GitLab** to inspect the remediation in the target repository.

If the run is interrupted by quota or rate-limit errors, the backend saves a checkpoint and the incident can be resumed from the API.

---

## Scenario Reference

| ID | Module | Bug Type | Target File |
|----|--------|----------|-------------|
| INC-101 | currency | Logic regression | `currency/converter.py` |
| INC-102 | auth | Null pointer | `auth/session_service.py` |
| INC-103 | billing | Dependency mismatch | `requirements.txt` |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| API URL not configured | Missing `NEXT_PUBLIC_API_BASE_URL` | Copy `frontend/.env.example` → `.env.local` |
| Repository validation FAIL | Invalid PAT or repo path | Check `GITLAB_PAT` and repository spelling |
| Gemini quota failure | API rate limit | Wait or use a different key |
| Missing runtime logs | Log path not generated locally | Run benchmark trigger or set valid log path |
| Validation failed | Patch didn't match source exactly | Re-run; check Gemini output quality |

---

## CLI Alternative

For headless evaluation without the UI:

```bash
python run_scenario.py INC-101 \
  --target-repo swankystark20-group/incidentops-demo-app \
  --target-branch main \
  --target-app-path invoice-app \
  --application-log-path invoice-app/application.log
```

Benchmark harness (3 runs per scenario):

```bash
cd tools/benchmark
python run_benchmark.py --runs 3
```
