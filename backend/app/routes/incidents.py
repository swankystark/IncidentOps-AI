import asyncio
import json as _json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from ..config import get_target_repo, settings
from ..database import get_db, log_to_db, refresh_incident_metrics
from ..incident_registry import (
    delete_incident_template,
    get_incident_template,
    load_incident_templates,
    target_app_path,
    target_app_path_for,
    upsert_incident_template,
)
from ..models import (
    Incident,
    IncidentCreate,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentTemplate,
    PlatformMetricsResponse,
)
from ..agents.graph import compiled_graph
from ..agents.state import AgentState

router = APIRouter(prefix="/incidents", tags=["incidents"])

_QUOTA_MARKERS = ["429", "resource_exhausted", "quota", "rate limit", "rate_limit"]

def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _QUOTA_MARKERS)

def _json_safe_state(state: dict) -> str:
    """Serialize AgentState to JSON, dropping non-serializable keys."""
    safe = {}
    for k, v in state.items():
        try:
            _json.dumps(v)
            safe[k] = v
        except (TypeError, ValueError):
            safe[k] = str(v)
    return _json.dumps(safe)

def _save_checkpoint(incident_id: int, state: dict, failure_reason: str):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        db.query(Incident).filter(Incident.id == incident_id).update({
            "checkpoint_state": _json_safe_state(state),
            "failure_reason": failure_reason,
            "status": "WAITING_FOR_RETRY",
        })
        db.commit()
    finally:
        db.close()

# Background task executor for LangGraph
async def execute_incident_agent_flow(
    incident_id: int,
    ticket_id: str,
    title: str,
    description: str,
    incident_template: dict,
    target_repo: str,
    target_branch: str,
    target_app_path_value: str,
    application_log_path_value: str,
):
    """Executes the LangGraph incident responder workflow in a background thread."""
    try:
        # 1. Trigger the actual application bug to generate the application.log file
        import subprocess
        import sys
        import os
        
        python_path = sys.executable
        trigger = incident_template.get("trigger") or {}
        trigger_script_name = trigger.get("script", "trigger_bug.py")
        target_path = target_app_path_for(target_app_path_value)
        trigger_script = target_path / trigger_script_name
        trigger_args = trigger.get("args") or [ticket_id]
        
        log_to_db(incident_id, "System", f"Triggering application bug for ticket {ticket_id} to generate runtime logs...", level="INFO")
        
        result = subprocess.run(
            [python_path, str(trigger_script), *trigger_args],
            capture_output=True,
            text=True,
            cwd=str(target_path)
        )

        from ..incident_registry import application_log_path_for
        log_path = application_log_path_for(application_log_path_value)
        if log_path.exists():
            log_to_db(incident_id, "System", f"Bug triggered successfully; runtime log generated at '{log_path}'.", level="INFO")
        else:
            log_to_db(incident_id, "System", f"Warning: runtime log was not generated. trigger stdout: {result.stdout}, stderr: {result.stderr}", level="WARNING")

        # 2. Initialize LangGraph AgentState dict
        initial_state: AgentState = {
            "incident_db_id": incident_id,
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "incident_template": incident_template,
            "target_repo": target_repo,
            "target_branch": target_branch,
            "target_app_path": target_app_path_value,
            "application_log_path": application_log_path_value,
            "shared_context": None,
            "gitlab_evidence": None,
            "cicd_evidence": None,
            "log_evidence": None,
            "root_cause": None,
            "confidence_score": None,
            "affected_file": None,
            "evidence_chain": None,
            "pinned_commit_sha": None,
            "investigation_timeline": [],
            "patch_explanation": None,
            "target_content": None,
            "replacement_content": None,
            "patch_diff": None,
            "validation_passed": None,
            "validation_logs": None,
            "validation_retry_count": 0,
            "gitlab_mr_url": None,
            "rca_report": None,
            "current_step": "PLANNING",
            "repo_context": None,
            "failure_reason": None,
        }
        
        # Run graph execution
        await compiled_graph.ainvoke(initial_state)
        refresh_incident_metrics(incident_id)
    except Exception as e:
        # Check if this is a quota/rate-limit error — checkpoint for resume
        if _is_quota_error(e):
            log_to_db(incident_id, "System", f"Quota/rate-limit error detected: {e}. State checkpointed for resume.", level="WARNING")
            _save_checkpoint(incident_id, {}, "quota_exhausted")
        else:
            log_to_db(incident_id, "System", f"Workflow execution halted by critical system failure: {e}", level="ERROR")
            from ..database import SessionLocal
            db = SessionLocal()
            try:
                db.query(Incident).filter(Incident.id == incident_id).update({"status": "FAILED"})
                db.commit()
            finally:
                db.close()
        refresh_incident_metrics(incident_id)

async def _resume_from_checkpoint(incident_id: int, checkpoint_state: dict):
    """Re-invoke the graph from a saved checkpoint state."""
    try:
        log_to_db(incident_id, "System", f"Resuming workflow from checkpoint (step: {checkpoint_state.get('current_step', 'UNKNOWN')})...")
        await compiled_graph.ainvoke(checkpoint_state)
        refresh_incident_metrics(incident_id)
    except Exception as e:
        if _is_quota_error(e):
            log_to_db(incident_id, "System", f"Quota error during resume: {e}. Re-checkpointed.", level="WARNING")
            _save_checkpoint(incident_id, checkpoint_state, "quota_exhausted")
        else:
            log_to_db(incident_id, "System", f"Resume failed: {e}", level="ERROR")
            from ..database import SessionLocal
            db = SessionLocal()
            try:
                db.query(Incident).filter(Incident.id == incident_id).update({"status": "FAILED"})
                db.commit()
            finally:
                db.close()
        refresh_incident_metrics(incident_id)

@router.get("", response_model=List[IncidentResponse])
def list_incidents(db: Session = Depends(get_db)):
    """Retrieve all incidents from the SQLite database."""
    return db.query(Incident).order_by(Incident.created_at.desc()).all()

@router.get("/templates", response_model=List[IncidentTemplate])
def list_incident_templates():
    """Return JSON-backed incident templates that can be run without code changes."""
    return load_incident_templates()

@router.post("/templates", response_model=IncidentTemplate)
def save_incident_template(template: IncidentTemplate):
    """Create or update a JSON-backed incident template."""
    try:
        return upsert_incident_template(template.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.delete("/templates/{ticket_id}")
def remove_incident_template(ticket_id: str):
    if not delete_incident_template(ticket_id):
        raise HTTPException(status_code=404, detail="Incident template not found")
    return {"deleted": True}

@router.get("/metrics/summary", response_model=PlatformMetricsResponse)
def get_platform_metrics(db: Session = Depends(get_db)):
    """Aggregate persisted incident-response metrics for the dashboard."""
    from ..models import IncidentMetric

    metrics = db.query(IncidentMetric).all()
    total = len(metrics)
    if total == 0:
        return PlatformMetricsResponse(
            total_incidents=0,
            average_investigation_time_seconds=0,
            evidence_sources_correlated=0,
            files_analyzed=0,
            average_root_cause_confidence=0,
            validation_success_rate=0,
            patch_success_rate=0,
            merge_requests_created=0,
        )

    return PlatformMetricsResponse(
        total_incidents=total,
        average_investigation_time_seconds=sum(m.investigation_time_seconds for m in metrics) / total,
        evidence_sources_correlated=sum(m.evidence_sources_correlated for m in metrics),
        files_analyzed=sum(m.files_analyzed for m in metrics),
        average_root_cause_confidence=sum(m.root_cause_confidence for m in metrics) / total,
        validation_success_rate=sum(1 for m in metrics if m.validation_success) / total,
        patch_success_rate=sum(1 for m in metrics if m.patch_success) / total,
        merge_requests_created=sum(1 for m in metrics if m.merge_request_created),
    )

@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """Fetch details of a single incident including its chronological execution logs."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.post("", response_model=IncidentResponse)
def trigger_incident(
    payload: IncidentCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """Triggers an incident investigation from a dynamic template or custom payload."""
    scenario_id = payload.scenario_id or payload.ticket_id
    template = get_incident_template(scenario_id) or {}
    target_repo = payload.target_repo or get_target_repo()
    target_branch = payload.target_branch or settings.GITLAB_TARGET_BRANCH
    target_app_path_value = payload.target_app_path if payload.target_app_path is not None else settings.TARGET_APP_PATH
    application_log_path_value = payload.application_log_path if payload.application_log_path is not None else settings.APPLICATION_LOG_PATH

    # Check if duplicate ticket exists
    existing = db.query(Incident).filter(Incident.ticket_id == payload.ticket_id).first()
    if existing:
        # Delete existing logs and incident to rerun fresh
        db.delete(existing)
        db.commit()
        
    db_incident = Incident(
        ticket_id=payload.ticket_id,
        scenario_id=scenario_id,
        title=payload.title or template.get("title"),
        description=payload.description or template.get("description"),
        module=template.get("module"),
        validation_strategy=template.get("validation"),
        target_repo=target_repo,
        target_branch=target_branch,
        target_app_path=target_app_path_value,
        application_log_path=application_log_path_value,
        status="INVESTIGATING",
        confidence_score=0
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    
    # Run the multi-agent orchestration in background tasks
    background_tasks.add_task(
        execute_incident_agent_flow, 
        db_incident.id, 
        db_incident.ticket_id, 
        db_incident.title, 
        db_incident.description,
        template,
        target_repo,
        target_branch,
        target_app_path_value,
        application_log_path_value,
    )
    
    return db_incident

@router.post("/{incident_id}/approve", response_model=IncidentResponse)
def approve_remediation(incident_id: int, db: Session = Depends(get_db)):
    """
    Human-in-the-loop review gate: Approves and merges the generated patch MR.
    Simulates merging the MR locally and closes the ticket status.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    incident.status = "RESOLVED"
    db.commit()
    
    # Write a confirmation log
    log_to_db(
        incident_id, 
        "Human Review Gate", 
        "Remediation patch approved by SRE. Merging changes to main branch and closing incident ticket.", 
        level="INFO"
    )
    refresh_incident_metrics(incident_id)
    
    return incident

@router.post("/{incident_id}/resume", response_model=IncidentResponse)
def resume_incident(
    incident_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Resume a previously failed/checkpointed incident workflow.
    Reloads the saved AgentState checkpoint from the database and
    re-invokes the LangGraph from the last known step.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status not in ("WAITING_FOR_RETRY", "FAILED"):
        raise HTTPException(
            status_code=400,
            detail=f"Incident status is '{incident.status}'; only WAITING_FOR_RETRY or FAILED incidents can be resumed.",
        )

    if not incident.checkpoint_state:
        raise HTTPException(
            status_code=400,
            detail="No checkpoint state saved for this incident. Cannot resume.",
        )

    try:
        checkpoint = _json.loads(incident.checkpoint_state)
    except _json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Corrupted checkpoint state.")

    # Clear the failure and mark as retrying
    incident.status = "INVESTIGATING"
    incident.failure_reason = None
    db.commit()
    db.refresh(incident)

    background_tasks.add_task(_resume_from_checkpoint, incident_id, checkpoint)
    return incident
