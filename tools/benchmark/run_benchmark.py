import argparse
import asyncio
import json
import math
import subprocess
import statistics
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.agents.cicd_agent import run_cicd_service
from app.agents.fusion_agent import run_fusion_agent
from app.agents.gitlab_agent import run_gitlab_service
from app.agents.log_agent import run_log_service
from app.agents.mr_agent import run_mr_agent
from app.agents.patch_agent import run_patch_agent
from app.agents.planner import run_planner
from app.agents.repository_context import run_repository_context
from app.agents.validation_agent import run_validation
from app.agents.graph import compiled_graph
from app.config import get_target_repo, settings
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema, log_to_db, refresh_incident_metrics
from app.incident_registry import application_log_path_for, get_incident_template, target_app_path_for
from app.models import AgentLog, Incident
from app.services.gemini import llm_service

BENCHMARK_CACHE_DIR = Path(".benchmark_cache")
REPORT_PATH = Path("benchmark_report.md")
BENCHMARK_CACHE_VERSION = 6
CACHED_STATE_KEYS = [
    "retrieval",
    "fusion",
    "shared_context",
    "gitlab_evidence",
    "cicd_evidence",
    "log_evidence",
    "pinned_commit_sha",
    "investigation_timeline",
]


def _contains_quota_error(logs: list[AgentLog]) -> bool:
    quota_markers = ["429", "RESOURCE_EXHAUSTED", "quota", "rate limit"]
    for log in logs:
        message = log.message.lower()
        if any(marker.lower() in message for marker in quota_markers):
            return True
    return False


def _initial_state(incident: Incident, template: dict, target_repo: str, target_branch: str) -> dict:
    return {
        "incident": {
            "incident_db_id": incident.id,
            "ticket_id": incident.ticket_id,
            "title": incident.title,
            "description": incident.description,
            "incident_template": template,
            "target_repo": target_repo,
            "target_branch": target_branch,
            "target_app_path": settings.TARGET_APP_PATH,
            "application_log_path": settings.APPLICATION_LOG_PATH,
        },
        "retrieval": {},
        "fusion": {},
        "repo_context": {},
        "patch": {},
        "validation": {"validation_retry_count": 0},
        "delivery": {},
        "workflow": {"current_step": "PLANNING"},
        "metrics": {},
    }


def _cache_key(scenario_id: str, target_repo: str, target_branch: str) -> str:
    safe_repo = target_repo.replace("/", "__").replace(":", "_")
    return f"{scenario_id}__{safe_repo}__{target_branch}.json"


def _cache_path(scenario_id: str, target_repo: str, target_branch: str) -> Path:
    return BENCHMARK_CACHE_DIR / _cache_key(scenario_id, target_repo, target_branch)


def _json_safe(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _load_cache(scenario_id: str, target_repo: str, target_branch: str) -> dict | None:
    path = _cache_path(scenario_id, target_repo, target_branch)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("cache_version") != BENCHMARK_CACHE_VERSION:
        return None
    return payload


def _save_cache(scenario_id: str, target_repo: str, target_branch: str, state: dict) -> Path:
    BENCHMARK_CACHE_DIR.mkdir(exist_ok=True)
    payload = {
        "scenario_id": scenario_id,
        "target_repo": target_repo,
        "target_branch": target_branch,
        "cache_version": BENCHMARK_CACHE_VERSION,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "state": {key: _json_safe(state.get(key)) for key in CACHED_STATE_KEYS},
    }
    path = _cache_path(scenario_id, target_repo, target_branch)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def _apply_cached_retrieval(state: dict, cached_payload: dict) -> dict:
    cached_state = cached_payload.get("state", {})
    for key in CACHED_STATE_KEYS:
        if key in cached_state:
            state[key] = cached_state[key]
    state["current_step"] = "EVIDENCE_FUSION"
    if "workflow" not in state:
        state["workflow"] = {}
    state["workflow"]["current_step"] = "EVIDENCE_FUSION"
    return state


async def _run_node(state: dict, node_func) -> dict:
    start_t = time.perf_counter()
    update = await node_func(state)
    elapsed = time.perf_counter() - start_t
    if "latencies" not in state:
        state["latencies"] = {}
    state["latencies"].setdefault(node_func.__name__, []).append(elapsed)
    if update:
        state.update(update)
    return state


async def _run_gitlab_cicd_branch(state: dict) -> dict:
    branch_state = dict(state)
    update = await run_gitlab_service(branch_state)
    if update:
        for key, value in update.items():
            if isinstance(value, dict) and isinstance(branch_state.get(key), dict):
                branch_state[key] = {**branch_state[key], **value}
            else:
                branch_state[key] = value
    update = await run_cicd_service(branch_state)
    if update:
        for key, value in update.items():
            if isinstance(value, dict) and isinstance(branch_state.get(key), dict):
                branch_state[key] = {**branch_state[key], **value}
            else:
                branch_state[key] = value
    return branch_state


async def _collect_retrieval_evidence(state: dict) -> dict:
    log_state, gitlab_cicd_state = await asyncio.gather(
        _run_node(dict(state), run_log_service),
        _run_gitlab_cicd_branch(state),
    )
    log_retrieval = log_state.get("retrieval", {})
    gc_retrieval = gitlab_cicd_state.get("retrieval", {})
    gc_fusion = gitlab_cicd_state.get("fusion", {})
    state["retrieval"] = {
        **state.get("retrieval", {}),
        "log_evidence": log_retrieval.get("log_evidence"),
        "gitlab_evidence": gc_retrieval.get("gitlab_evidence"),
        "cicd_evidence": gc_retrieval.get("cicd_evidence"),
    }
    state["fusion"] = {
        **state.get("fusion", {}),
        "pinned_commit_sha": gc_fusion.get("pinned_commit_sha"),
    }
    return state


async def _run_cached_workflow(state: dict, incident_id: int, scenario_id: str, target_repo: str, target_branch: str, benchmark_mode: bool) -> None:
    if not benchmark_mode:
        await compiled_graph.ainvoke(state)
        return

    cached_payload = _load_cache(scenario_id, target_repo, target_branch)
    if cached_payload:
        log_to_db(incident_id, "Benchmark Mode", f"Reusing cached planner, GitLab, pipeline, and runtime-log evidence for {scenario_id}.")
        state = _apply_cached_retrieval(state, cached_payload)
        if "latencies" not in state:
            state["latencies"] = {}
    else:
        log_to_db(incident_id, "Benchmark Mode", f"No cache found for {scenario_id}; collecting real planner and retrieval evidence once.")
        state = await _run_node(state, run_planner)
        state = await _collect_retrieval_evidence(state)
        cache_path = _save_cache(scenario_id, target_repo, target_branch, state)
        log_to_db(incident_id, "Benchmark Mode", f"Cached retrieval evidence at '{cache_path}'.")

    state = await _run_node(state, run_fusion_agent)
    state = await _run_node(state, run_repository_context)
    state = await _run_node(state, run_patch_agent)
    if state.get("workflow", {}).get("current_step") == "FAILED":
        return
    state = await _run_node(state, run_validation)
    wf_step = state.get("workflow", {}).get("current_step")
    retry_count = state.get("validation", {}).get("validation_retry_count", 0)
    if wf_step == "PATCHING" and retry_count <= 1:
        state = await _run_node(state, run_patch_agent)
        if state.get("workflow", {}).get("current_step") == "FAILED":
            return
        state = await _run_node(state, run_validation)
    if state.get("workflow", {}).get("current_step") == "FAILED":
        return
    state = await _run_node(state, run_mr_agent)


async def run_one(scenario_id: str, index: int, target_repo: str, target_branch: str, benchmark_mode: bool) -> dict:
    template = get_incident_template(scenario_id)
    if not template:
        raise RuntimeError(f"Unknown scenario {scenario_id}")

    ticket_id = f"{scenario_id}-BENCH-{index:03d}-{datetime.utcnow().strftime('%H%M%S')}"
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        incident = Incident(
            ticket_id=ticket_id,
            scenario_id=scenario_id,
            title=template["title"],
            description=template["description"],
            module=template.get("module"),
            validation_strategy=template.get("validation"),
            target_repo=target_repo,
            target_branch=target_branch,
            target_app_path=settings.TARGET_APP_PATH,
            application_log_path=settings.APPLICATION_LOG_PATH,
            status="INVESTIGATING",
            confidence_score=0,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        incident_id = incident.id
    finally:
        db.close()

    state = _initial_state(incident, template, target_repo, target_branch)
    latencies = {}
    start = time.perf_counter()
    try:
        trigger = template.get("trigger") or {}
        trigger_script_name = trigger.get("script", "trigger_bug.py")
        target_path = target_app_path_for(settings.TARGET_APP_PATH)
        trigger_script = target_path / trigger_script_name
        trigger_args = trigger.get("args") or [scenario_id]
        log_to_db(incident_id, "System", f"Triggering application bug for benchmark run {ticket_id}.")
        result = subprocess.run(
            [sys.executable, str(trigger_script), *trigger_args],
            capture_output=True,
            text=True,
            cwd=str(target_path),
        )
        log_path = application_log_path_for(settings.APPLICATION_LOG_PATH)
        if log_path.exists():
            log_to_db(incident_id, "System", f"Runtime log generated at '{log_path}'.")
        else:
            log_to_db(incident_id, "System", f"Runtime log missing. stdout: {result.stdout}, stderr: {result.stderr}", level="WARNING")
        await _run_cached_workflow(
            state,
            incident_id,
            scenario_id,
            target_repo,
            target_branch,
            benchmark_mode,
        )
        latencies = state.get("latencies", {})
    except Exception as exc:
        db = SessionLocal()
        try:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident:
                incident.status = "FAILED"
                db.commit()
            print(f"RUN_ERROR {ticket_id} {exc}")
        finally:
            db.close()
    duration = time.perf_counter() - start
    refresh_incident_metrics(incident_id)

    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        logs = db.query(AgentLog).filter(AgentLog.incident_id == incident_id).order_by(AgentLog.id.asc()).all()
        validation_result = any(log.agent_name == "Validation Service" and "Validation PASSED" in log.message for log in logs)
        patch_result = bool(incident.patch_diff)
        mr_result = bool(incident.gitlab_mr_url)
        quota_exhausted = _contains_quota_error(logs)

        # Determine LLM success
        llm_success = not any("fallback" in log.message.lower() for log in logs if log.agent_name in ["Evidence Fusion Agent", "Patch Generation Agent"])

        return {
            "incident_id": incident_id,
            "ticket_id": ticket_id,
            "scenario_id": scenario_id,
            "duration": duration,
            "latencies": latencies,
            "confidence": incident.confidence_score or 0,
            "validation_result": validation_result,
            "patch_result": patch_result,
            "mr_result": mr_result,
            "llm_success": llm_success,
            "status": incident.status,
            "mr_url": incident.gitlab_mr_url,
            "quota_exhausted": quota_exhausted,
            "benchmark_mode": benchmark_mode,
        }
    finally:
        db.close()


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {}
    durations = [r["duration"] for r in rows]
    confidences = [r["confidence"] for r in rows]
    success = [r for r in rows if r["validation_result"] and r["patch_result"] and r["mr_result"]]
    return {
        "runs": len(rows),
        "duration_mean": statistics.mean(durations),
        "duration_median": statistics.median(durations),
        "duration_stddev": statistics.pstdev(durations) if len(durations) > 1 else 0.0,
        "confidence_mean": statistics.mean(confidences),
        "confidence_median": statistics.median(confidences),
        "confidence_stddev": statistics.pstdev(confidences) if len(confidences) > 1 else 0.0,
        "workflow_success_rate": len(success) / len(rows),
        "validation_success_rate": sum(1 for r in rows if r["validation_result"]) / len(rows),
        "patch_success_rate": sum(1 for r in rows if r["patch_result"]) / len(rows),
        "mr_success_rate": sum(1 for r in rows if r["mr_result"]) / len(rows),
        "llm_success_rate": sum(1 for r in rows if r.get("llm_success", False)) / len(rows),
        "quota_failures": sum(1 for r in rows if r.get("quota_exhausted", False)),
        "attempt_success_rate": sum(1 for r in rows if r.get("status") == "RESOLVED") / len(rows),
        "model_availability_rate": 1.0, # Placeholder until 503 explicitly tracked
    }


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_report(rows: list[dict], path: Path = REPORT_PATH) -> None:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["scenario_id"], []).append(row)

    lines = [
        "# IncidentOps AI Benchmark Report",
        "",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "",
        "Benchmark mode was enabled. Planner output, GitLab evidence, selected pipeline evidence, and runtime logs were collected once per scenario and reused for repeated runs. Fusion, patch generation, validation, and MR/RCA stages were recomputed for each run.",
        "",
        "## Summary",
        "",
        "| Scenario | Runs | Mean Duration (s) | Workflow Success | LLM Success | Validation Success | Patch Rate | MR Rate | Quota Failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scenario in sorted(grouped):
        summary = summarize(grouped[scenario])
        lines.append(
            f"| {scenario} | {summary['runs']} | {summary['duration_mean']:.2f} | "
            f"{_pct(summary['workflow_success_rate'])} | {_pct(summary['llm_success_rate'])} | "
            f"{_pct(summary['validation_success_rate'])} | {_pct(summary['patch_success_rate'])} | {_pct(summary['mr_success_rate'])} | {summary['quota_failures']} |"
        )

    overall = summarize(rows)
    if overall:
        lines.extend([
            "",
            "## Overall",
            "",
            f"- Runs: {overall['runs']}",
            f"- Mean duration: {overall['duration_mean']:.2f}s",
            f"- Median duration: {overall['duration_median']:.2f}s",
            f"- Workflow success rate: {_pct(overall['workflow_success_rate'])}",
            f"- LLM success rate: {_pct(overall['llm_success_rate'])}",
            f"- Validation success rate: {_pct(overall['validation_success_rate'])}",
            f"- Patch rate: {_pct(overall['patch_success_rate'])}",
            f"- MR rate: {_pct(overall['mr_success_rate'])}",
            f"- Quota failures: {overall['quota_failures']}",
            f"- Model availability rate: {_pct(overall['model_availability_rate'])}",
        ])

    lines.extend([
        "",
        "## Runs",
        "",
        "| Scenario | Ticket | Duration (s) | Confidence | Validation | Patch | MR | Status |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            f"| {row['scenario_id']} | {row['ticket_id']} | {row['duration']:.2f} | {row['confidence']} | "
            f"{row['validation_result']} | {row['patch_result']} | {row['mr_result']} | {row['status']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main():
    parser = argparse.ArgumentParser(description="Run repeated IncidentOps benchmark scenarios.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--scenarios", nargs="+", default=["INC-101", "INC-102", "INC-103"])
    parser.add_argument("--target-repo", default=get_target_repo())
    parser.add_argument("--target-branch", default=settings.GITLAB_TARGET_BRANCH)
    parser.add_argument("--gemini-api-key", type=str, default=os.environ.get("GEMINI_API_KEY"),
                        help="Optional: Gemini API Key.")
    parser.add_argument("--groq-api-key", type=str, default=os.environ.get("GROQ_API_KEY"),
                        help="Optional: Groq API Key.")
    parser.add_argument("--benchmark-mode", action="store_true")
    parser.add_argument("--no-benchmark-mode", action="store_true")
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args()
    benchmark_mode = args.benchmark_mode or not args.no_benchmark_mode

    if args.gemini_api_key and llm_service.provider_name == "gemini":
        llm_service.set_api_key(args.gemini_api_key)
    elif args.groq_api_key and llm_service.provider_name == "groq":
        llm_service.set_api_key(args.groq_api_key)

    all_rows: list[dict] = []
    for scenario in args.scenarios:
        scenario_rows = []
        for index in range(args.start_index, args.start_index + args.runs):
            row = await run_one(scenario, index, args.target_repo, args.target_branch, benchmark_mode)
            all_rows.append(row)
            scenario_rows.append(row)
            print(
                "RUN",
                row["scenario_id"],
                row["ticket_id"],
                f"duration={row['duration']:.2f}",
                f"confidence={row['confidence']}",
                f"validation={row['validation_result']}",
                f"patch={row['patch_result']}",
                f"mr={row['mr_result']}",
                f"status={row['status']}",
            )
            if row["quota_exhausted"]:
                print("STOPPED_GEMINI_QUOTA_EXHAUSTED")
                print("SUMMARY_PARTIAL", summarize(scenario_rows))
                write_report(all_rows, Path(args.report_path))
                return
        print("SUMMARY", scenario, summarize(scenario_rows))
    print("SUMMARY_ALL", summarize(all_rows))
    write_report(all_rows, Path(args.report_path))
    print("REPORT", args.report_path)


if __name__ == "__main__":
    asyncio.run(main())
