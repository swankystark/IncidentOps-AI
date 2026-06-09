import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..database import SessionLocal
from ..models import AgentLog, Incident

router = APIRouter(prefix="/stream", tags=["stream"])

@router.get("/{incident_id}")
async def stream_incident_updates(incident_id: int):
    """
    Server-Sent Events (SSE) route to push real-time agent log timeline
    updates and global state transitions to the Next.js frontend dashboard.
    """
    async def log_generator():
        last_log_id = 0
        active = True
        
        while active:
            db = SessionLocal()
            try:
                # 1. Fetch any new agent activity logs since last poll
                logs = db.query(AgentLog).filter(
                    AgentLog.incident_id == incident_id,
                    AgentLog.id > last_log_id
                ).order_by(AgentLog.id.asc()).all()
                
                for log in logs:
                    last_log_id = log.id
                    log_packet = {
                        "type": "agent_log",
                        "id": log.id,
                        "agent_name": log.agent_name,
                        "message": log.message,
                        "level": log.level,
                        "timestamp": log.timestamp.isoformat()
                    }
                    yield f"data: {json.dumps(log_packet)}\n\n"
                
                # 2. Fetch the incident to push the current status parameters to UI panels
                incident = db.query(Incident).filter(Incident.id == incident_id).first()
                if incident:
                    # Build investigation timeline from agent log timestamps
                    all_logs = db.query(AgentLog).filter(
                        AgentLog.incident_id == incident_id
                    ).order_by(AgentLog.id.asc()).all()
                    
                    # Deduplicate to first log per agent name for timeline
                    seen_agents = {}
                    timeline_labels = {
                        "Planner Agent": "Planner: Investigation scoped",
                        "GitLab Service": "GitLab: Commit history retrieved",
                        "CI/CD Service": "CI/CD: Pipeline status retrieved",
                        "Log Service": "Logs: Error anomalies detected",
                        "Evidence Fusion Agent": "Fusion: Root cause correlated",
                        "Patch Generation Agent": "Patch: Code fix generated",
                        "Validation Service": "Validation: Tests executed",
                        "MR & RCA Agent": "MR & RCA: Report created",
                        "Human Review Gate": "Human: Patch approved & merged",
                    }
                    timeline = []
                    for log in all_logs:
                        if log.agent_name not in seen_agents:
                            seen_agents[log.agent_name] = True
                            label = timeline_labels.get(log.agent_name, log.agent_name)
                            timeline.append({
                                "time": log.timestamp.strftime("%H:%M:%S"),
                                "label": label,
                                "agent": log.agent_name
                            })
                    
                    status_packet = {
                        "type": "status_update",
                        "status": incident.status,
                        "confidence_score": incident.confidence_score,
                        "gitlab_mr_url": incident.gitlab_mr_url,
                        "patch_diff": incident.patch_diff,
                        "rca_report": incident.rca_report,
                        "investigation_timeline": timeline
                    }
                    yield f"data: {json.dumps(status_packet)}\n\n"
                    
                    # Stop streaming once terminal states are reached (or human merges)
                    if incident.status in ["RESOLVED", "FAILED"]:
                        active = False
            except Exception as e:
                print(f"Error in SSE log stream: {e}")
                active = False
            finally:
                db.close()
            
            # Wait for next update poll (500ms)
            await asyncio.sleep(0.5)

    return StreamingResponse(log_generator(), media_type="text/event-stream")
