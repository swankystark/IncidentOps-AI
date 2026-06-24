# Benchmark Scenario Routing Root Cause Report

Generated: 2026-06-23T00:00:00Z

## Question

The latest 3-run benchmark appeared to route `INC-101` and `INC-102` into a `requirements.txt` dependency patch path and produced `Patch target content was not found in source`.

This report checks whether that is:

- a real regression
- a benchmark harness artifact
- a stub contamination issue

## Bottom Line

This is a **benchmark harness artifact with stub contamination**, not a real product regression.

The production scenario mapping still points to the correct files:

- `INC-101` -> `currency/converter.py`
- `INC-102` -> `auth/session_service.py`
- `INC-103` -> `requirements.txt`

The dependency-path behavior came from the temporary Groq stub / replay path, plus cached benchmark state, not from the incident registry or the real patch-targeting implementation.

## Evidence

### Previous 30-run benchmark

The historical 30-run benchmark in `tools/benchmark/final_benchmark_report.md` shows:

- Workflow success rate: `83.3%`
- Validation success rate: `100.0%`
- Patch success rate: `100.0%`
- MR success rate: `83.3%`
- Mean files analyzed: `0.0`

It also records the intended per-scenario target files:

- `INC-101` -> `currency/converter.py`
- `INC-102` -> `auth/session_service.py`
- `INC-103` -> `requirements.txt`

That baseline does not show scenario selection drift.

### Latest 3-run benchmark

The latest 3-run benchmark in `tools/benchmark/benchmark_report.md` is not equivalent to the 30-run baseline because the benchmark path was changed during investigation:

- benchmark cache version was bumped
- replay behavior was adjusted
- a temporary scenario-aware Groq stub was introduced and exercised

Earlier reruns during the investigation did produce the suspicious dependency-routing symptom, but that symptom came from the harness path, not from `incidents.json`.

### Current code path

The real benchmark runner still maps scenarios from the incident registry:

- `tools/benchmark/run_benchmark.py` loads the incident template with `get_incident_template(scenario_id)`
- the template's `target_file` drives `affected_file`
- patch targeting runs through `CodeTargetingService.target_code(...)`

The registry itself still defines:

- `INC-101` -> `currency/converter.py`
- `INC-102` -> `auth/session_service.py`
- `INC-103` -> `requirements.txt`

## Answers To The Questions

### 1. Why is INC-101 generating a dependency patch?

In the contaminated benchmark path, the temporary stub and cached replay state caused the fusion / patch-generation inputs to collapse into the dependency scenario. That produced a `requirements.txt` patch path even though the real incident registry maps `INC-101` to `currency/converter.py`.

### 2. Why is INC-102 generating a dependency patch?

Same root cause as `INC-101`: the harness contamination shifted the scenario signal away from the incident registry mapping and into the dependency branch.

### 3. Did the scenario-aware stub alter patch-generation behavior?

**Yes.** The temporary scenario-aware stub affected the model responses that feed evidence fusion and patch selection. That changed downstream targeting decisions in the benchmark harness.

### 4. Is the benchmark exercising the real Patch Targeting Service path?

**Partially yes, but not cleanly enough to trust the contaminated run as baseline.**

The real runner does call `CodeTargetingService.target_code(...)`, but the earlier contaminated benchmark reused replay/stub state that changed which file reached that service. The service itself is still the real patch-targeting path.

## Classification

| Scenario | Classification |
| --- | --- |
| `INC-101` dependency patch symptom | Benchmark harness artifact + stub contamination |
| `INC-102` dependency patch symptom | Benchmark harness artifact + stub contamination |
| Scenario selection drift in the contaminated rerun | Stub contamination issue |
| Real production regression | Not supported by the evidence |

## Comparison Against The 30-Run Baseline

| Metric | Previous 30-run benchmark | Latest 3-run benchmark |
| --- | ---: | ---: |
| Workflow success | 83.3% | 33.3% |
| Validation success | 100.0% | 33.3% |
| Patch success | 100.0% | 100.0% |
| MR success | 83.3% | 100.0% |
| Mean files analyzed | 0.0 | 1.0 |

The 30-run benchmark remains the baseline for platform behavior. The 3-run result is useful for instrumentation checks, but not as a replacement baseline.

## Conclusion

Do **not** treat the latest 3-run benchmark as the new baseline.

The dependency-patch symptom is best classified as a **benchmark harness artifact with stub contamination**, not a confirmed regression in scenario routing or patch targeting.

