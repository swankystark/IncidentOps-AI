import asyncio
import argparse
import os
import sys

# Load env variables (re-locating the .env path)
from dotenv import load_dotenv
load_dotenv()

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.database import engine, Base, SessionLocal
from app.config import get_target_repo, settings
from app.incident_registry import get_incident_template
from app.models import Incident, AgentLog
from app.agents.graph import compiled_graph
from app.agents.state import AgentState

async def run_scenario_cli():
    parser = argparse.ArgumentParser(description="Run an IncidentOps AI scenario from incidents.json.")
    parser.add_argument("ticket_id", nargs="?", default=settings.DEFAULT_INCIDENT_ID)
    parser.add_argument("--target-repo", default=get_target_repo())
    parser.add_argument("--target-branch", default=settings.GITLAB_TARGET_BRANCH)
    parser.add_argument("--target-app-path", default=settings.TARGET_APP_PATH)
    parser.add_argument("--application-log-path", default=settings.APPLICATION_LOG_PATH)
    args = parser.parse_args()
    template = get_incident_template(args.ticket_id) or {}
    ticket_id = args.ticket_id.upper()
    title = template.get("title", f"Incident {ticket_id}")
    description = template.get("description", "Ad hoc incident investigation.")

    print("=" * 70)
    print("         INCIDENTOPS AI - CLI VERIFICATION SCENARIO RUNNER")
    print(f"         Scenario: {ticket_id}")
    print(f"         Target Repo: {args.target_repo} ({args.target_branch})")
    print("=" * 70)
    
    # 1. Initialize SQLite Database
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Clear existing currency tickets to permit fresh clean runs
        existing = db.query(Incident).filter(Incident.ticket_id == ticket_id).first()
        if existing:
            db.delete(existing)
            db.commit()
            
        # 2. Plant Demo Incident Ticket
        incident = Incident(
            ticket_id=ticket_id,
            title=title,
            description=description,
            module=template.get("module"),
            validation_strategy=template.get("validation"),
            target_repo=args.target_repo,
            target_branch=args.target_branch,
            target_app_path=args.target_app_path,
            application_log_path=args.application_log_path,
            status="INVESTIGATING",
            confidence_score=0
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        
        incident_id = incident.id
        print(f"[System] Created Incident Record ID: {incident_id} ({incident.ticket_id})")
        print("[System] Starting multi-agent LangGraph execution loop...")
        print("-" * 70)
        
        # 3. Define LangGraph initial execution state
        initial_state: AgentState = {
            "incident_db_id": incident_id,
            "ticket_id": incident.ticket_id,
            "title": incident.title,
            "description": incident.description,
            "incident_template": template,
            "target_repo": args.target_repo,
            "target_branch": args.target_branch,
            "target_app_path": args.target_app_path,
            "application_log_path": args.application_log_path,
            "shared_context": None,
            "gitlab_evidence": None,
            "cicd_evidence": None,
            "log_evidence": None,
            "root_cause": None,
            "confidence_score": None,
            "affected_file": None,
            "evidence_chain": None,
            "patch_explanation": None,
            "target_content": None,
            "replacement_content": None,
            "patch_diff": None,
            "validation_passed": None,
            "validation_logs": None,
            "validation_retry_count": 0,
            "gitlab_mr_url": None,
            "rca_report": None,
            "current_step": "PLANNING"
        }
        
        # 4. Chronological console logger to print agent execution events
        async def console_logger():
            last_id = 0
            while True:
                session = SessionLocal()
                try:
                    logs = session.query(AgentLog).filter(
                        AgentLog.incident_id == incident_id,
                        AgentLog.id > last_id
                    ).order_by(AgentLog.id.asc()).all()
                    
                    for log in logs:
                        last_id = log.id
                        timestamp_str = log.timestamp.strftime("%H:%M:%S")
                        print(f" {timestamp_str} | [{log.agent_name}] {log.message}")
                finally:
                    session.close()
                
                # Check status
                session_check = SessionLocal()
                status = "INVESTIGATING"
                try:
                    inc = session_check.query(Incident).filter(Incident.id == incident_id).first()
                    if inc:
                        status = inc.status
                finally:
                    session_check.close()
                    
                if status in ["RESOLVED", "RESOLVING", "FAILED"]:
                    # Sleep to let trailing logs write
                    await asyncio.sleep(1.0)
                    break
                await asyncio.sleep(0.5)

        # Run graph execution and logging loop side-by-side
        await asyncio.gather(
            compiled_graph.ainvoke(initial_state),
            console_logger()
        )
        
        # 5. Output Summary Report
        db.refresh(incident)
        print("=" * 70)
        print("                      AGENT WORKFLOW RESULTS SUMMARY")
        print("=" * 70)
        print(f"Incident Ticket:  {incident.ticket_id} - {incident.title}")
        print(f"Remediation Status: {incident.status}")
        print(f"Diagnosis Confidence: {incident.confidence_score}%")
        print(f"GitLab Merge Request URL: {incident.gitlab_mr_url}")
        print("-" * 70)
        print("GENERATED CODE FIX PATCH:")
        print(incident.patch_diff)
        print("-" * 70)
        print("RCA REPORT SUMMARY:")
        print(incident.rca_report)
        print("=" * 70)
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_scenario_cli())
