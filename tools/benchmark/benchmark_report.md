# IncidentOps AI Benchmark Report

Generated: 2026-06-05T06:13:09.073685Z

Benchmark mode was enabled. Planner output, GitLab evidence, selected pipeline evidence, and runtime logs were collected once per scenario and reused for repeated runs. Fusion, patch generation, validation, and MR/RCA stages were recomputed for each run.

## Summary

| Scenario | Runs | Mean Duration (s) | Median Duration (s) | Success Rate | Mean Confidence | Validation Rate | Patch Rate | MR Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| INC-101 | 3 | 49.93 | 50.62 | 100.0% | 98.0 | 100.0% | 100.0% | 100.0% |
| INC-102 | 3 | 41.58 | 45.91 | 66.7% | 97.0 | 66.7% | 66.7% | 66.7% |

## Overall

- Runs: 6
- Mean duration: 45.75s
- Median duration: 48.84s
- Success rate: 83.3%
- Mean confidence: 97.5
- Validation rate: 83.3%
- Patch rate: 83.3%
- MR rate: 83.3%

## Runs

| Scenario | Ticket | Duration (s) | Confidence | Validation | Patch | MR | Status |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| INC-101 | INC-101-BENCH-001-060834 | 47.06 | 98 | True | True | True | RESOLVED |
| INC-101 | INC-101-BENCH-002-060921 | 50.62 | 98 | True | True | True | RESOLVED |
| INC-101 | INC-101-BENCH-003-061012 | 52.10 | 98 | True | True | True | RESOLVED |
| INC-102 | INC-102-BENCH-001-061104 | 55.03 | 98 | True | True | True | RESOLVED |
| INC-102 | INC-102-BENCH-002-061159 | 45.91 | 98 | True | True | True | RESOLVED |
| INC-102 | INC-102-BENCH-003-061245 | 23.81 | 95 | False | False | False | FAILED |
