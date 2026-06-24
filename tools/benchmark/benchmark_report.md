# IncidentOps AI Benchmark Report

Generated: 2026-06-23T02:51:09.524526Z

Benchmark mode was enabled. Planner output, GitLab evidence, selected pipeline evidence, and runtime logs were collected once per scenario and reused for repeated runs. Fusion, patch generation, validation, and MR/RCA stages were recomputed for each run.

## Summary

| Scenario | Runs | Mean Duration (s) | Workflow Success | LLM Success | Validation Success | Patch Rate | MR Rate | Quota Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| INC-101 | 10 | 30.51 | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 0 |
| INC-102 | 10 | 16.58 | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 0 |
| INC-103 | 10 | 23.41 | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 0 |

## Overall

- Runs: 30
- Mean duration: 23.50s
- Median duration: 22.20s
- Workflow success rate: 0.0%
- LLM success rate: 100.0%
- Validation success rate: 0.0%
- Patch rate: 0.0%
- MR rate: 0.0%
- Quota failures: 0
- Model availability rate: 100.0%

## Runs

| Scenario | Ticket | Duration (s) | Confidence | Validation | Patch | MR | Status |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| INC-101 | INC-101-BENCH-001-023923 | 29.48 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-002-023952 | 29.42 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-003-024022 | 41.25 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-004-024103 | 29.24 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-005-024132 | 29.70 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-006-024202 | 29.17 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-007-024231 | 29.21 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-008-024301 | 28.98 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-009-024330 | 29.23 | 0 | False | False | False | FAILED |
| INC-101 | INC-101-BENCH-010-024359 | 29.46 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-001-024428 | 26.57 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-002-024455 | 15.04 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-003-024510 | 15.01 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-004-024525 | 19.77 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-005-024545 | 14.77 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-006-024600 | 15.16 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-007-024615 | 14.78 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-008-024630 | 15.12 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-009-024645 | 14.60 | 0 | False | False | False | FAILED |
| INC-102 | INC-102-BENCH-010-024700 | 14.95 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-001-024715 | 31.22 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-002-024746 | 22.22 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-003-024808 | 21.75 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-004-024830 | 22.45 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-005-024852 | 22.09 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-006-024914 | 21.90 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-007-024936 | 21.57 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-008-024958 | 22.08 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-009-025020 | 26.64 | 0 | False | False | False | FAILED |
| INC-103 | INC-103-BENCH-010-025047 | 22.18 | 0 | False | False | False | FAILED |
