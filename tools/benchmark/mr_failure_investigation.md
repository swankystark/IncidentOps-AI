# MR Failure Investigation

Generated: 2026-06-22T00:00:00Z

## Scope

Historical benchmark failures: `INC-102-BENCH-009-083940`, `INC-102-BENCH-010-084006`, `INC-103-BENCH-002-084148`, `INC-103-BENCH-007-084516`, `INC-103-BENCH-010-084739`.

Observed benchmark summary:

- Patch success: 100%
- Validation success: 100%
- Workflow success: 83.3%
- MR success: 83.3%

## Execution Path

The MR delivery path is:

1. `tools/benchmark/run_benchmark.py::_run_cached_workflow`
2. `backend/app/agents/mr_agent.py::run_mr_agent`
3. `backend/app/services/gitlab.py::GitLabService.create_merge_request`
4. `backend/app/services/gitlab.py::GitLabService.create_merge_request_real`

Branch delivery uses the same flow earlier in `run_mr_agent` through `GitLabService.create_branch`.

## Failure Classification

| Ticket | Failure point | Root cause classification | Evidence-based note |
| --- | --- | --- | --- |
| `INC-102-BENCH-009-083940` | Branch creation never produced a confirmed branch before MR creation | Branch creation retry issue + GitLab API transient failure | No MR exists in the retained run state. This is not a duplicate branch, duplicate MR, or permissions issue. |
| `INC-102-BENCH-010-084006` | Same as above | Branch creation retry issue + GitLab API transient failure | Neighboring runs succeeded with the same token, which argues against permissions. |
| `INC-103-BENCH-002-084148` | MR POST path after branch/commit | MR reconciliation failure + idempotency issue | Branch and commit exist, but the run never recovered a created MR from a failed or lost MR POST. |
| `INC-103-BENCH-007-084516` | MR POST path after branch/commit | MR reconciliation failure + idempotency issue | Same signature as `INC-103-BENCH-002-084148`. |
| `INC-103-BENCH-010-084739` | MR already existed while the benchmark still reported failure | Race condition + benchmark artifact | The delivery happened, but the benchmark bookkeeping marked the run failed before it reconciled the successful MR. |

## Root Cause Analysis

The failure mechanism is not a single bug. It is a delivery-side reconciliation gap:

- Branch creation failures are retried, but the code only treats a false return or `httpx.HTTPError` as recoverable. The historical failure pattern shows that some runs still never observed a confirmed branch before moving on.
- MR creation currently recovers only when GitLab returns explicit `409 Conflict`. That is too narrow for the historical failure shape. If GitLab creates the MR but the response is lost, or if GitLab returns a transient failure after the side effect is already durable, the run can still fail even though the MR exists.
- One historical run already proves the benchmark can race its own bookkeeping: the MR existed while the benchmark marked the run failed.

## Minimal Implementation Plan

1. Add a small MR reconciliation helper in `GitLabService` that can query for an open MR by `source_branch` and `target_branch`.
2. Call that helper after any failed MR create attempt before returning failure.
3. Keep branch creation retry logic as-is, but reuse the same reconciliation pattern if the branch POST is ambiguous.
4. Add one regression test for the lost-response MR path and one for branch reconciliation.
5. Rerun the benchmark and confirm MR success and workflow success both reach 100% without regressing validation or patch success.

## Non-goals

- No new agents.
- No Redis, Kafka, queues, or workers.
- No architecture rewrite.
- No speculative retry expansion beyond the observed delivery failure path.

