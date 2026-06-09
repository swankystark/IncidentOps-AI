# IncidentOps AI — Public Claim Audit

**Audit date:** 2026-06-09  
**Scope:** README.md, docs/resume_bullets.md, docs/demo_walkthrough.md, GitHub project description (in resume_bullets.md §3), LinkedIn description (resume_bullets.md §2), interview scripts (§4–§5)

**Primary evidence sources:**

| Source | Path | Role |
|--------|------|------|
| Benchmark report | `tools/benchmark/benchmark_report.md` | Quantitative success, confidence, duration |
| Benchmark runner | `tools/benchmark/run_benchmark.py` | Metric definitions (`summarize()`) |
| LangGraph workflow | `backend/app/agents/graph.py` | Agent count, execution order |
| Incident registry | `incidents.json` | Scenario count (3 templates) |
| Approve endpoint | `backend/app/routes/incidents.py` | MR merge behavior |
| Platform acceptance | `docs/platform_acceptance_report.md` | Multi-repo evidence retrieval |
| Limitations | `docs/limitations.md` | Repository-agnostic caveats |

---

## Metric Definitions (Benchmark Harness)

From `run_benchmark.py` → `summarize()`:

| Metric | Calculation | Sample used in published report |
|--------|-------------|--------------------------------|
| **Success rate** | Runs where `validation_result AND patch_result AND mr_result` | n = **6** |
| **Validation rate** | Runs with log `"Validation PASSED"` from Validation Service | n = 6 |
| **Patch rate** | Runs with non-empty `incident.patch_diff` | n = 6 |
| **MR rate** | Runs with non-empty `incident.gitlab_mr_url` | n = 6 |
| **Mean confidence** | `statistics.mean(confidence_score)` per run | n = 6 |
| **Mean duration** | `statistics.mean(duration)` wall-clock seconds per run | n = 6 |

**Important:** The published report includes **only INC-101 and INC-102** (3 runs each). **INC-103 was not included** in the reported results despite being a default scenario in the harness and having a cache file.

---

## Quantitative Claims — Full Audit

### 1. End-to-end success rate: 83% / 83.3%

| Field | Value |
|-------|-------|
| **Claim locations** | README §Benchmark Results, resume §1/§2/§4, interview §5 |
| **Source file** | `tools/benchmark/benchmark_report.md` (Overall: Success rate 83.3%) |
| **Calculation** | 5 successful runs ÷ 6 total = 83.3% (success = validation + patch + MR all true) |
| **Sample size** | **n = 6** (INC-101 × 3, INC-102 × 3) |
| **Verdict** | **SUPPORTED** — for the 6-run sample |

**Corrected wording when scenario count matters:**

> **83% end-to-end success rate (5/6 benchmark runs)** across INC-101 and INC-102 on the GitLab demo repository.

**Do not say:** “83% across 3 scenarios” — INC-103 was not part of this benchmark sample.

---

### 2. Mean RCA confidence: 97.5%

| Field | Value |
|-------|-------|
| **Claim locations** | README, LinkedIn highlights, resume §1/§4/§5 |
| **Source file** | `tools/benchmark/benchmark_report.md` (Mean confidence: 97.5) |
| **Calculation** | mean(98, 98, 98, 98, 98, 95) = 97.5 |
| **Sample size** | **n = 6** |
| **Verdict** | **SUPPORTED** |

---

### 3. Mean investigation-to-MR time: ~46 seconds

| Field | Value |
|-------|-------|
| **Claim locations** | Resume §1 (“reduced mean investigation-to-MR time to ~46 seconds”), interview §4/§5 |
| **Source file** | `tools/benchmark/benchmark_report.md` (Mean duration: 45.75s) |
| **Calculation** | Wall-clock mean of 6 runs; rounded to ~46s |
| **Sample size** | **n = 6** |
| **Verdict** | **PARTIALLY SUPPORTED** |

**Issue:** The word **“reduced”** implies a before/after baseline. No baseline measurement exists in any report.

**Corrected wording:**

> Achieved **~46-second mean end-to-end investigation-to-MR time** (45.75s measured; n=6 benchmark runs on the GitLab demo repository).

---

### 4. INC-101 success rate: 100%

| Field | Value |
|-------|-------|
| **Source** | `benchmark_report.md` — INC-101 Success Rate 100.0% |
| **Calculation** | 3/3 runs passed validation, patch, and MR |
| **Sample size** | **n = 3** |
| **Verdict** | **SUPPORTED** |

---

### 5. INC-101 mean confidence: 98%

| Field | Value |
|-------|-------|
| **Source** | `benchmark_report.md` — INC-101 Mean Confidence 98.0 |
| **Sample size** | **n = 3** (all confidence = 98) |
| **Verdict** | **SUPPORTED** |

---

### 6. INC-101 mean duration: ~50s

| Field | Value |
|-------|-------|
| **Source** | `benchmark_report.md` — INC-101 Mean Duration 49.93s |
| **Sample size** | **n = 3** |
| **Verdict** | **SUPPORTED** (~50s rounding) |

---

### 7. INC-102 success rate: 66.7%

| Field | Value |
|-------|-------|
| **Source** | `benchmark_report.md` — INC-102 Success Rate 66.7% |
| **Calculation** | 2/3 runs successful; one failed (confidence 95, validation/patch/MR false) |
| **Sample size** | **n = 3** |
| **Verdict** | **SUPPORTED** |

---

### 8. INC-102 mean confidence: 97%

| Field | Value |
|-------|-------|
| **Source** | `benchmark_report.md` — INC-102 Mean Confidence 97.0 |
| **Calculation** | mean(98, 98, 95) = 97 |
| **Sample size** | **n = 3** |
| **Verdict** | **SUPPORTED** |

---

### 9. INC-102 mean duration: ~42s

| Field | Value |
|-------|-------|
| **Source** | `benchmark_report.md` — INC-102 Mean Duration 41.58s |
| **Sample size** | **n = 3** |
| **Verdict** | **SUPPORTED** |

---

### 10. “83% across 3 production-like scenarios”

| Field | Value |
|-------|-------|
| **Claim locations** | Resume §1 |
| **Source** | `incidents.json` has 3 scenarios; `benchmark_report.md` only reports 2 |
| **Sample size** | Claim implies n=9 or 3 scenarios; actual n=6 over 2 scenarios |
| **Verdict** | **UNSUPPORTED** |

**Corrected wording:**

> **83% end-to-end success rate (5/6 runs)** on **two benchmarked scenarios** (INC-101, INC-102) from a registry of three demo incidents.

---

### 11. “Benchmarked on three planted bugs… 83% success” (interview §4)

| Field | Value |
|-------|-------|
| **Verdict** | **PARTIALLY SUPPORTED** |

Three planted bugs exist in `incidents.json` and the demo repo, but the **83% figure comes from only two scenarios (6 runs)**. INC-103 has cache evidence but **no published benchmark runs**.

**Corrected wording:**

> I benchmarked the platform on planted bugs in a demo GitLab repo. In the latest 6-run evaluation (INC-101 and INC-102, 3 runs each), end-to-end success was **83%**, mean confidence **97.5%**, and mean duration **~46 seconds**. A third scenario (INC-103) is defined but not included in that published sample.

---

### 12. LinkedIn: “83% success rate, 97.5% mean RCA confidence across 6 runs”

| Field | Value |
|-------|-------|
| **Verdict** | **SUPPORTED** |

This is the most precise public claim in the package.

---

### 13. “7 LangGraph agents”

| Field | Value |
|-------|-------|
| **Claim locations** | Resume §1 |
| **Source** | `backend/app/agents/graph.py` — **8 LangGraph nodes** |

| Node | Type |
|------|------|
| planner | Agent |
| log_service | Service |
| gitlab_service | Service |
| cicd_service | Service |
| evidence_fusion | Agent |
| patch_generation | Agent |
| validation_service | Service |
| mr_creation | Agent |

| Counting method | Total |
|-----------------|-------|
| All LangGraph nodes | **8** |
| Reasoning agents only (planner, fusion, patch, MR) | **4** |
| Agents + retrieval/validation services (excl. planner) | **7** if counting GitLab + CI/CD + Log + Fusion + Patch + Validation + MR |

| **Verdict** | **PARTIALLY SUPPORTED** |

The “7” count is defensible only if you adopt a non-standard definition (e.g., exclude Planner, count 7 executors after planning). The graph registers **8 nodes**. Documentation elsewhere says “4 agents + 4 services.”

**Corrected wording:**

> Orchestrating **8 LangGraph workflow nodes** (4 reasoning agents and 4 retrieval/validation services)

or

> Orchestrating a **multi-agent LangGraph pipeline** with planner, evidence fusion, patch generation, and MR/RCA agents backed by GitLab, CI/CD, log, and validation services.

---

### 14. Parallel evidence retrieval

| Field | Value |
|-------|-------|
| **Claim locations** | README, LinkedIn, interview §4/§5, demo_walkthrough §2 |
| **Source** | `backend/app/agents/graph.py` edges: `planner → log → gitlab → cicd → fusion` (**sequential**) |
| **UI behavior** | Dashboard displays three services as a parallel layer (presentation only) |
| **Verdict** | **PARTIALLY SUPPORTED** |

The **UI implies parallelism**; the **LangGraph execution order is sequential**. Services are logically independent retrievers but are not executed concurrently in the current graph.

**Corrected wording:**

> Collects evidence from GitLab, CI/CD, and runtime logs through dedicated retrieval services (currently orchestrated sequentially in LangGraph; parallel fan-out is a documented future improvement).

---

### 15. Repository-agnostic / “any GitLab repository”

| Field | Value |
|-------|-------|
| **Claim locations** | README, LinkedIn, GitHub description, interview |
| **Code evidence** | Per-incident `target_repo`, `target_branch`, `target_app_path`, `application_log_path`; `GitLabService.from_state()` |
| **Test evidence** | `docs/platform_acceptance_report.md` — GitLab file/pipeline retrieval tested on 3 public repos |
| **End-to-end benchmark** | Only `swankystark20-group/incidentops-demo-app` |
| **Limitations** | Pytest-only validation; local log path; LLM patch fidelity |
| **Verdict** | **PARTIALLY SUPPORTED** |

Configuration is repository-agnostic. **Validated end-to-end remediation** is demonstrated on **one benchmark repository**. Evidence retrieval alone was tested on three repos.

**Corrected wording:**

> **Repository-configurable by design** — each incident stores its own GitLab target. End-to-end patch/MR/validation benchmarks were run against one demo repository; GitLab evidence retrieval was smoke-tested on three public repositories.

---

### 16. MR creation claims

| Claim | Source | Verdict |
|-------|--------|---------|
| “Opens remediation merge requests” | `mr_agent.py` + benchmark MR rate 83.3% (5/6) | **SUPPORTED** for successful runs |
| “Opens merge requests with full RCA” | MR agent writes RCA markdown to GitLab MR | **SUPPORTED** on success path |
| “Approve & Merge” performs GitLab merge | `incidents.py` approve endpoint only sets `status=RESOLVED` | **UNSUPPORTED** — merge is **simulated** |
| Docstring: “Approves and merges the generated patch MR” | `incidents.py:238` | **UNSUPPORTED** — misleading vs implementation |

**Corrected wording:**

> Creates GitLab merge requests with AI-authored RCA on successful runs (**83% MR creation rate; n=6**). Human approval updates incident status locally; **GitLab MR merge is not yet wired to the API**.

---

### 17. Validation / patch / remediation claims

| Claim | Source | n | Verdict |
|-------|--------|---|---------|
| Validation rate 83.3% | benchmark_report.md | 6 | **SUPPORTED** |
| Patch rate 83.3% | benchmark_report.md | 6 | **SUPPORTED** |
| MR rate 83.3% | benchmark_report.md | 6 | **SUPPORTED** |
| “Generate validated patches” | Success requires pytest pass | 6 | **SUPPORTED** with sample caveat |
| “Minimal patch” | Qualitative; patch agent prompt | — | **PARTIALLY SUPPORTED** (not measured) |

---

### 18. Demo walkthrough: “~98% confidence” (INC-101 example)

| Field | Value |
|-------|-------|
| **Source** | INC-101 benchmark runs all scored 98 |
| **Sample size** | n = 3 for INC-101 |
| **Verdict** | **SUPPORTED** as illustrative example |

---

### 19. Next.js version “15” (README)

| Field | Value |
|-------|-------|
| **Source** | `frontend/package.json` → `"next": "16.2.6"` |
| **Verdict** | **UNSUPPORTED** (stale doc) |

**Corrected:** Next.js 16 (or “Next.js App Router” without version).

---

## Qualitative Claims (Non-quantitative)

| Claim | Verdict | Notes |
|-------|---------|-------|
| Autonomous Tier-3 incident response | PARTIALLY SUPPORTED | Marketing term; human review gate required |
| Real-time SSE dashboard | SUPPORTED | `routes/stream.py` |
| Pre-flight repository validation | SUPPORTED | `POST /api/config/repository/validate` |
| No hardcoded target repo in UI | SUPPORTED | Empty defaults + demo preset |
| Docker support | PARTIALLY SUPPORTED | Dockerfiles exist; backend path resolution in container untested |

---

## Recommended Corrected Resume Bullet

**Before (resume_bullets.md §1):**

> Built IncidentOps AI… **reduced** mean investigation-to-MR time to ~46 seconds by orchestrating **7 LangGraph agents**… **83% end-to-end success rate across 3 production-like scenarios**…

**After (defensible):**

> **Built IncidentOps AI**, an autonomous incident-response platform that achieves **~46-second mean end-to-end investigation-to-MR time** (n=6 benchmark runs) by orchestrating a **LangGraph multi-agent pipeline** (planner, evidence fusion, patch generation, MR/RCA, plus GitLab/CI/CD/log/validation services) to correlate GitLab commits, CI/CD failures, and runtime logs, generate pytest-validated patches with an **83% end-to-end success rate (5/6 runs)** on two demo scenarios, and open GitLab merge requests with AI-authored RCA reports — using **FastAPI, Next.js, Google Gemini, and GitLab API**.

---

## Recommended Corrected Two-Minute Interview Close

**Before:**

> I benchmarked it on three planted bugs in a demo repo: 83% end-to-end success…

**After:**

> In a 6-run benchmark on two demo scenarios in our GitLab test repo, the system achieved 83% end-to-end success, about 46 seconds average duration, and 97.5% mean RCA confidence. A third scenario is registered but wasn’t part of that evaluation sample.

---

## Summary Table

| Verdict | Count |
|---------|------:|
| SUPPORTED | 14 |
| PARTIALLY SUPPORTED | 9 |
| UNSUPPORTED | 4 |

**Highest-risk interview questions:**

1. “You said 3 scenarios — where is INC-103 in the benchmark?”
2. “Reduced from what baseline?”
3. “Are retrievers actually parallel?”
4. “Does Approve & Merge really merge on GitLab?”
5. “How many agents — 7 or 8?”

All five have corrected answers above.
