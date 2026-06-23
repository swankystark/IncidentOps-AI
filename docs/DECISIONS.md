# Design Decisions

This file records the choices that shape the current implementation.

## 1. LangGraph Is The Orchestration Spine

**Decision:** Use LangGraph for the incident workflow instead of a hand-rolled orchestrator.

**Why:** The workflow has clear stages, a retry loop, and a checkpoint/resume path. LangGraph makes that structure explicit.

**Consequence:** The graph is the best source of truth for execution order.

## 2. Retrieval Is Split By Responsibility

**Decision:** Keep logs, GitLab, and CI/CD as separate nodes.

**Why:** Each source has a different failure mode and latency profile.

**Consequence:** Evidence fusion can reason over independent streams instead of one monolithic fetch step.

## 3. CI/CD Depends On GitLab Context

**Decision:** Keep CI/CD downstream of GitLab rather than a fully parallel top-level branch.

**Why:** The GitLab service pins the commit SHA that CI/CD uses to select the relevant pipeline and job traces.

**Consequence:** The user-facing diagram should show the dependency, not a symmetric fan-out.

## 4. Repository Context Stays Deterministic

**Decision:** Use static analysis and GitLab reads for repository context.

**Why:** Import graphs, test discovery, and recent commits are faster and more predictable without an LLM.

**Consequence:** Patch generation gets richer context without adding model cost.

## 5. Validation Retires Once

**Decision:** Allow one automatic retry when validation fails.

**Why:** A single retry catches patch-formatting misses without hiding real regressions.

**Consequence:** Validation remains a gate, not a no-op.

## 6. Quota Failures Save A Checkpoint

**Decision:** Persist checkpoint state when model quota or rate limits interrupt the flow.

**Why:** The workflow can be resumed from the last known state.

**Consequence:** Recovery is operationally cheaper than rerunning the whole incident.
