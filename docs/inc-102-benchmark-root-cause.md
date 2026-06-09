# INC-102 Benchmark Root-Cause Report

Generated: 2026-06-05

## Executive Summary

INC-102 reported 66.7% success because the third benchmark run stopped during Patch Generation after Gemini returned `429 RESOURCE_EXHAUSTED`.

This was not a scenario-analysis failure, evidence-retrieval failure, validation failure, patch-quality failure, or GitLab MR failure. The system correctly identified the root cause in all three INC-102 runs. The failed run did not reach patch validation or MR creation because the benchmark policy requires stopping when the Gemini key is exhausted.

## Runs Analyzed

| Run | Ticket | Status | Confidence | Patch | Validation | MR |
| --- | --- | --- | ---: | --- | --- | --- |
| 1 | INC-102-BENCH-001-061104 | RESOLVED | 98 | Passed | Passed | Created |
| 2 | INC-102-BENCH-002-061159 | RESOLVED | 98 | Passed | Passed | Created |
| 3 | INC-102-BENCH-003-061245 | FAILED | 95 | Not generated | Not run | Not created |

Successful merge requests:

- https://gitlab.com/swankystark20-group/incidentops-demo-app/-/merge_requests/16
- https://gitlab.com/swankystark20-group/incidentops-demo-app/-/merge_requests/17

## Failure Point

Failed component: Patch Generation Agent

Failed run: `INC-102-BENCH-003-061245`

Error class: Gemini API quota exhaustion

Observed error:

```text
429 RESOURCE_EXHAUSTED
Quota exceeded for metric:
generativelanguage.googleapis.com/generate_content_free_tier_requests
limit: 20
model: gemini-2.5-flash
```

The run stopped before patch content was generated, so validation and MR creation could not execute.

## Evidence That Scenario Reasoning Worked

The failed run reused cached real retrieval evidence for INC-102:

- Planner output
- GitLab commit evidence
- GitLab source file evidence
- CI/CD failure evidence
- Runtime logs

The Evidence Fusion Agent still produced the correct root cause with 95% confidence:

```text
The validate_token function in auth/session_service.py fails to handle cases
where user_profile is None, leading to a TypeError when accessing
user_profile["email"].
```

This matches the expected INC-102 defect:

- A deleted or missing user profile returns `None`
- `validate_token()` dereferences that value
- The auth service crashes instead of invalidating the session cleanly

## Evidence Sources

GitLab evidence identified the relevant auth implementation commit:

- `f34a24e7` - `feat(auth): add session service, user lookup, and auth API endpoints`
- Commit message notes a known "null profile edge case"

CI/CD evidence identified the failing auth test:

- `tests/test_auth.py::test_validate_token_deleted_user_raises_attribute_error`
- Failure: `TypeError: 'NoneType' object is not subscriptable`
- Location: `auth/session_service.py:107`

Runtime logs confirmed the same failure mode:

- `TypeError: 'NoneType' object is not subscriptable`
- During token validation
- In `auth/session_service.py`

## Root Cause Of 66.7% Success

The benchmark counted the quota-interrupted run as a failed run:

```text
2 successful runs / 3 total runs = 66.7%
```

That number is mathematically correct for the partial benchmark output, but it conflates platform correctness with external model quota availability.

The underlying INC-102 workflow success rate for completed runs was:

```text
2 successful completed runs / 2 completed runs = 100%
```

The model-dependent availability rate for the batch was:

```text
2 patch calls completed / 3 attempted patch calls = 66.7%
```

## Conclusion

INC-102 did not fail because the platform could not investigate or remediate the incident. It failed because the Gemini free-tier quota was exhausted during the third patch-generation call.

The benchmark result should be reported as:

- Completed-run success rate: 100%
- Attempted-run success rate including quota interruption: 66.7%
- External model quota interruption: 1 run

## Recommended Fix

For benchmark reporting, separate workflow failures from infrastructure failures:

- `workflow_success_rate`: validation + patch + MR success for runs that reached model completion
- `attempt_success_rate`: success across all attempted runs
- `model_quota_failures`: count of runs stopped by external API quota
- `model_availability_rate`: non-quota-failed runs divided by attempted runs

This keeps the benchmark honest while avoiding the misleading impression that INC-102 remediation logic failed.
