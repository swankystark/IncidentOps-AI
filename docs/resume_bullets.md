# IncidentOps AI — Resume & Interview Package

---

## 1. Resume Bullet (XYZ Format)

**Built IncidentOps AI**, an autonomous incident-response platform that achieves **~46-second mean end-to-end investigation-to-MR time** (n=6 benchmark runs) by orchestrating a **LangGraph multi-agent pipeline** (planner, evidence fusion, patch generation, MR/RCA, plus GitLab/CI/CD/log/validation services) to correlate GitLab commits, CI/CD failures, and runtime logs, generate pytest-validated patches with an **83% end-to-end success rate (5/6 runs)** on two demo scenarios, and open GitLab merge requests with AI-authored RCA reports — using **FastAPI, Next.js, Google Gemini, and GitLab API**.

---

## 2. LinkedIn Project Description

**IncidentOps AI — Autonomous Tier-3 Incident Response**

Production incidents demand fast correlation across logs, pipelines, commits, and source code. IncidentOps AI automates that entire loop.

I designed and built a multi-agent system using LangGraph that targets configurable GitLab repositories, fuses evidence from GitLab, CI/CD, and runtime log retrieval services, generates pytest-validated patches, and opens merge requests with full root cause analysis reports.

**Stack:** FastAPI · LangGraph · Google Gemini · GitLab API · Next.js · SQLite · Docker

**Highlights:**
- Repository-configurable design — per-incident GitLab target with no hardcoded repo in UI
- Real-time SSE dashboard with orchestration map, RCA panel, and human review gate
- Benchmark evaluation: 83% success rate, 97.5% mean RCA confidence across 6 runs
- Pre-flight repository validation before workflow execution

🔗 GitHub: github.com/swankystark/IncidentOps-AI

---

## 3. GitHub Project Description

Autonomous incident-response platform that investigates configurable GitLab repositories, correlates evidence from commits/CI/logs, generates validated patches, and opens remediation MRs with RCA reports. Built with FastAPI, LangGraph, Gemini, and Next.js.

---

## 4. Two-Minute Interview Explanation

> "When a production incident fires, engineers waste critical time jumping between logs, CI dashboards, Git history, and source code before they can even propose a fix. I built IncidentOps AI to automate that investigation loop.
>
> The user picks an incident template and points the system at a GitLab repository. Before anything runs, they validate that the repo and branch are accessible. Then a LangGraph workflow kicks off: a planner scopes the investigation, dedicated services collect evidence from GitLab, CI/CD pipelines, and runtime logs, and a fusion agent uses Gemini to correlate everything into a root cause with a confidence score.
>
> From there, a patch agent generates a minimal fix, a validation service runs pytest against the target, and an MR agent commits the patch and opens a GitLab merge request with a full RCA report. The frontend streams all of this live via SSE — you watch agents light up on an orchestration map, see the RCA panel populate, review the diff, and approve at a human review gate. Note: approval updates incident status locally; GitLab MR merge is not yet wired to the API.
>
> In a 6-run benchmark on two demo scenarios in our GitLab test repo, the system achieved 83% end-to-end success, about 46 seconds average duration, and 97.5% mean RCA confidence. Every run stores its own target repo, branch, and paths, so the platform is not tied to one application."

---

## 5. Ten-Minute Deep Dive Explanation

### Problem & Motivation (1 min)

On-call engineers follow a repeatable but slow pattern: read the alert, check logs, find the failing pipeline, identify the suspicious commit, read the source, hypothesize root cause, write a patch, run tests, open an MR. Each step uses a different tool. IncidentOps AI collapses that into one orchestrated workflow with a human review gate at the end.

### Architecture (2 min)

**Frontend:** Single-page Next.js dashboard. No hardcoded API URL — configured via `NEXT_PUBLIC_API_BASE_URL`. Empty form defaults; demo preset loads benchmark values on demand. SSE streaming for live agent logs and status updates. Dedicated RCA panel parsing structured report sections. Visible alert banners for GitLab failures, Gemini quota, missing logs, validation failures, and MR errors.

**Backend:** FastAPI with three route groups — incidents (CRUD + metrics), config (Gemini key + repository validation), stream (SSE). SQLite stores incidents, agent logs, and computed metrics. LangGraph compiles a directed workflow graph.

**Agents vs Services:** Agents reason (planner, fusion, patch, MR/RCA). Services retrieve (GitLab, CI/CD, logs) or verify (validation). LangGraph currently orchestrates retrieval sequentially; the dashboard presents the three retrievers as a coordinated evidence layer.

### Workflow Deep Dive (3 min)

1. **Incident creation** — POST `/api/incidents` with template ID and per-run repo config. Backend deletes any prior run with the same ticket ID and starts a background task.

2. **Planner** — Reads `incidents.json` template: module, validation strategy, target file, test target, priority signals. Sets investigation scope.

3. **Evidence retrieval** — GitLab Service fetches commits and source files, pins a commit SHA. CI/CD Service selects the most relevant pipeline on the target branch. Log Service reads the configured application log path and extracts anomalies.

4. **Evidence fusion** — Gemini structured output (`EvidenceFusionOutput`): root cause, confidence 0–1, affected file, evidence chain. Persisted to DB as interim RCA. If confidence is low, refinement can be requested.

5. **Patch generation** — Gemini reads the affected file from GitLab evidence and produces `target_content` / `replacement_content` for a unified diff. One retry on validation failure.

6. **Validation** — Strategy pattern: `currency_validator`, `auth_validator`, `dependency_validator` are aliases over `generic_pytest`. Runs the `test_target` from the incident template.

7. **MR & RCA** — Gemini generates full markdown RCA. GitLab Service creates branch, commits patch, opens MR. Status moves to RESOLVING; human approval updates incident status locally (GitLab merge API not yet wired).

### Repository-Configurable Design (1 min)

Every incident stores `target_repo`, `target_branch`, `target_app_path`, `application_log_path`. `GitLabService.from_state(state)` instantiates a client per run. The benchmark demo app lives in a separate GitLab repo; this GitHub repo contains only the platform. Pre-flight validation (`POST /api/config/repository/validate`) checks project + branch without starting the workflow.

### Evaluation & Results (1.5 min)

Benchmark harness in `tools/benchmark/`: latest published sample is **6 runs** (INC-101 × 3, INC-102 × 3) with cached retrieval evidence. INC-103 is registered but not in that sample. Results:
- INC-101: 100% success (n=3), 98% confidence
- INC-102: 66.7% success (n=3), 97% confidence
- Overall: 83.3% success (5/6), 97.5% mean confidence, ~46s mean duration

### Limitations & Future Work (1.5 min)

- Pytest-only validation; needs npm/Maven/Go strategies for polyglot repos
- Local log path dependency; production needs Datadog/Splunk connector
- LLM patch must exactly match source block or validation fails
- Approve endpoint simulates merge; production would call GitLab merge API
- FastAPI BackgroundTasks not durable; would move to Celery/ARQ
- SSE polls SQLite; would use Redis pub/sub at scale

### Closing (30 sec)

The project demonstrates end-to-end systems thinking: multi-agent orchestration, real API integrations, structured LLM output, human-in-the-loop safety, repository-agnostic configuration, and measurable evaluation — packaged for anyone to clone, configure, and run without prior context.
