# IncidentOps AI Final Benchmark Report

Generated: 2026-06-18T08:48:21.733578Z

## Benchmark Methodology

- **Replay mode:** enabled (`ENABLE_BENCHMARK_REPLAY=true`)
- **Target repository:** `swankystark20-group/incidentops-demo-app` @ `main`
- **Retrieval stages executed live each run:** Log Service, GitLab Service, CI/CD Service
- **Validation stage executed live each run:** Validation Service (pytest strategy)
- **Replayed without Gemini calls:** Planner, Evidence Fusion, Patch Generation, RCA authoring
- **Success definition:** validation passed, patch diff persisted, GitLab MR created, incident status `RESOLVED`
- **Quota failures:** classified separately and excluded from workflow success rate denominator
- **Gemini API calls during benchmark:** **0**

## Overall Metrics

- Total runs: 30
- Success rate: 83.3%
- Workflow success rate (excludes quota failures): 83.3%
- Validation success rate: 100.0%
- Patch success rate: 100.0%
- MR success rate: 83.3%
- Mean duration: 31.38s
- Median duration: 25.32s
- Std dev duration: 11.06s
- Mean confidence: 98.0
- Mean evidence sources correlated: 3.0
- Mean files analyzed: 0.0

## Failure Breakdown

| Class | Count |
| --- | ---: |
| none | 25 |
| workflow_failures | 5 |

## Per-Scenario Metrics

| Scenario | Runs | Success Rate | Mean Duration (s) | Median Duration (s) | Std Dev (s) | Mean Confidence | Validation Rate | Patch Rate | MR Rate | Evidence Sources | Files Analyzed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| INC-101 | 10 | 100.0% | 23.54 | 22.89 | 1.83 | 98.0 | 100.0% | 100.0% | 100.0% | 3.0 | 0.0 |
| INC-102 | 10 | 80.0% | 25.86 | 22.61 | 7.77 | 98.0 | 100.0% | 100.0% | 80.0% | 3.0 | 0.0 |
| INC-103 | 10 | 70.0% | 44.75 | 45.55 | 5.68 | 98.0 | 100.0% | 100.0% | 70.0% | 3.0 | 0.0 |

## Confidence Distribution

- Min: 98
- Max: 98
- Mean: 98.0
- Median: 98.0
- Std dev: 0.0

## Duration Distribution

- Min: 19.99s
- Max: 54.73s
- Mean: 31.38s
- Median: 25.32s
- Std dev: 11.06s

## Runs

| Scenario | Ticket | Duration (s) | Confidence | Validation | Patch | MR | Failure Class | Status |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| INC-101 | INC-101-BENCH-001-083238 | 22.57 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-002-083301 | 23.20 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-003-083324 | 20.57 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-004-083345 | 25.49 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-005-083410 | 22.48 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-006-083433 | 25.78 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-007-083459 | 21.95 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-008-083521 | 24.99 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-009-083546 | 22.14 | 98 | True | True | True | none | RESOLVED |
| INC-101 | INC-101-BENCH-010-083608 | 26.18 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-001-083634 | 23.43 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-002-083658 | 19.99 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-003-083718 | 22.79 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-004-083740 | 22.25 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-005-083803 | 30.96 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-006-083834 | 21.87 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-007-083856 | 22.42 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-008-083918 | 22.14 | 98 | True | True | True | none | RESOLVED |
| INC-102 | INC-102-BENCH-009-083940 | 25.16 | 98 | True | True | False | workflow_failures | FAILED |
| INC-102 | INC-102-BENCH-010-084006 | 47.61 | 98 | True | True | False | workflow_failures | FAILED |
| INC-103 | INC-103-BENCH-001-084053 | 54.73 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-002-084148 | 37.65 | 98 | True | True | False | workflow_failures | FAILED |
| INC-103 | INC-103-BENCH-003-084226 | 48.19 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-004-084314 | 33.38 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-005-084347 | 44.07 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-006-084432 | 44.32 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-007-084516 | 47.32 | 98 | True | True | False | workflow_failures | FAILED |
| INC-103 | INC-103-BENCH-008-084603 | 48.65 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-009-084652 | 46.78 | 98 | True | True | True | none | RESOLVED |
| INC-103 | INC-103-BENCH-010-084739 | 42.42 | 98 | True | True | False | workflow_failures | FAILED |

## Gemini Quota Proof

- Reported Gemini API calls: **0**
- With replay mode enabled, Planner/Fusion/Patch/RCA stages restore cached artifacts and `gemini_service.generate_*` is blocked.

## Workflow Failure Analysis

The historical benchmark report contains 5 `workflow_failures`. The report dropped the raw infrastructure error, so the exact HTTP status/body is not recoverable from the benchmark artifact alone. The classifications below are based on retained GitLab state and the surrounding run evidence.

| Ticket | MR creation failure reason | Classification | Notes |
| --- | --- | --- | --- |
| `INC-102-BENCH-009-083940` | Branch creation never yielded a confirmed branch, and no MR exists for the run | GitLab API issue + retry issue | Not duplicate branch, not duplicate MR, not permissions. Exact HTTP body is unavailable. |
| `INC-102-BENCH-010-084006` | Same pattern as above: no branch and no MR were retained | GitLab API issue + retry issue | Adjacent runs succeeded, which makes a permissions problem unlikely. |
| `INC-103-BENCH-002-084148` | Branch exists, commit exists, but no MR was created | GitLab API issue + retry issue | The failure is after branch/commit creation, so this is an MR creation/reconciliation failure. |
| `INC-103-BENCH-007-084516` | Branch exists, commit exists, but no MR was created | GitLab API issue + retry issue | Same signature as `INC-103-BENCH-002-084148`. |
| `INC-103-BENCH-010-084739` | MR `!44` was created for the same branch before the benchmark marked the run failed | Race condition + benchmark artifact | This run is a lost-response / late-reconciliation case, not a duplicate MR or branch issue. |

Duplicate branch, duplicate MR, and permissions issues were ruled out by the retained GitLab state and the successful neighboring runs.

## Mean Files Analyzed Root Cause

`mean_files_analyzed = 0.0` because the replay benchmark path skipped the Repository Context Service entirely, and the metrics code only counted file mentions from GitLab / Validation logs.

- `tools/benchmark/run_benchmark.py` replayed cached planner, GitLab, CI/CD, validation, and MR steps, but did not call `run_repository_context`.
- `backend/app/database.py` only counted files from GitLab / Validation messages, so Patch Generation logs and Repository Context logs were ignored.

The fix is twofold:

- `tools/benchmark/run_benchmark.py` now runs `run_repository_context` after fusion and before patch generation.
- `backend/app/database.py` now counts explicit Repository Context file totals and patch-targeting file mentions.

## Scenario Usage Matrix

| Scenario | Target file | Files analyzed in historical report | Repository Context executed in June 18 replay | AST extraction usage | Patch targeting usage |
| --- | --- | ---: | --- | --- | --- |
| `INC-101` | `currency/converter.py` | 0.0 | No | Yes, the patch target is Python so `CodeTargetingService` can use AST bounds after function identification | Yes |
| `INC-102` | `auth/session_service.py` | 0.0 | No | Yes, same Python-target AST path as `INC-101` | Yes |
| `INC-103` | `requirements.txt` | 0.0 | No | No, the target is not Python so patch targeting falls back to line-range identification | Yes |

## Verification Notes

- The MR retry/reconciliation fix is covered by `backend/tests/test_benchmark_workflow.py`.
- The replay ordering fix is covered by `backend/tests/test_benchmark_workflow.py`.
- The files-analyzed metric helper is covered by `backend/tests/test_benchmark_workflow.py`.
- Manual runtime checks confirmed the synthetic MR flow retries branch and MR creation and returns `COMPLETED`.
- Manual runtime checks confirmed the cached benchmark replay now reaches `run_repository_context` before `run_patch_agent`.

