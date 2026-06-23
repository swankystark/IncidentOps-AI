# IncidentOps AI Benchmarks

This document summarizes the benchmark harness, what it measures, and the most recent reported numbers in the repo.

## Benchmark Modes

| Mode | Description | When to use |
|------|-------------|-------------|
| Live | Full execution with all stages active | Production-like validation |
| Replay | Reuse cached retrieval and rerun LLM stages | Prompt and patch iteration |
| Infrastructure | Cache every LLM output and exercise deterministic code paths | CI smoke testing |

## Core Metrics

| Metric | Meaning |
|--------|---------|
| `workflow_success_rate` | Full pipeline completion from planner through MR |
| `llm_success_rate` | All LLM-backed nodes completed successfully |
| `validation_success_rate` | Validation passed |
| `patch_success_rate` | Patch diff was generated and validated |
| `mr_success_rate` | MR was created or synthesized |
| `model_availability_rate` | 1 minus quota failure rate |
| `attempt_success_rate` | Success per attempt, including the validation retry loop |

## Cache Layout

```text
.benchmark_cache/
├── {scenario}__{repo}__{branch}.json
    ├── planner_output
    ├── gitlab_evidence
    ├── cicd_evidence
    ├── log_evidence
    ├── pinned_commit_sha
    └── investigation_timeline
```

## Run Commands

```bash
# Fresh run
rm -rf .benchmark_cache
MODEL_PROVIDER=groq PYTHONPATH=backend python -m tools.benchmark.run_benchmark --runs 3 --scenarios INC-101 INC-102 INC-103 --no-benchmark-mode

# Replay run
MODEL_PROVIDER=groq PYTHONPATH=backend python -m tools.benchmark.run_benchmark --runs 3 --scenarios INC-101 INC-102 INC-103 --benchmark-mode

# CI-safe run
SKIP_MR_CREATION=true MODEL_PROVIDER=groq PYTHONPATH=backend python -m tools.benchmark.run_benchmark --runs 3 --scenarios INC-101 INC-102 INC-103 --no-benchmark-mode
```

## Reported Results In Repo

The checked-in benchmark report records:

- `workflow_success_rate`: 100.0%
- `llm_success_rate`: 100.0%
- `validation_success_rate`: 100.0%
- `patch_success_rate`: 100.0%
- `mr_success_rate`: 100.0%
- `quota_failures`: 0
- `model_availability_rate`: 100.0%
- `mean_duration`: 79.3s

Per-scenario numbers in the report:

| Scenario | Success | Mean confidence | Mean duration |
|----------|---------|------------------|---------------|
| INC-101 | 100.0% | 98.0 | 49.93s |
| INC-102 | 66.7% | 97.0 | 41.58s |
| INC-103 | present in harness, not in the published sample | - | - |

## Benchmark Interpretation

1. The reported 83.3% overall result is based on 6 runs across INC-101 and INC-102.
2. INC-103 exists in the harness, but the published report does not include it.
3. The benchmark is only as good as the configured GitLab repo, API access, and model availability.
4. Validation is real pytest execution, not a stub.

## Latency Breakdown

| Stage | Typical time |
|-------|--------------|
| Planner | 2-5s |
| Log Service | 0.1-0.5s |
| GitLab Service | 1-3s |
| CI/CD Service | 10-30s |
| Evidence Fusion | 2-5s |
| Repository Context | 1-2s |
| Patch Targeting | 2-4s |
| Patch Generation | 2-5s |
| Validation | 10-30s |
| MR + RCA | 5-10s |

## Source Files

- `tools/benchmark/run_benchmark.py`
- `tools/benchmark/benchmark_report.md`
- `tools/benchmark/final_benchmark_report.md`
