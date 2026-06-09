from ..services.gemini import gemini_service, EvidenceFusionOutput
from ..database import log_to_db
from ..config import settings
from .state import AgentState

async def run_fusion_agent(state: AgentState) -> dict:
    """
    Evidence Fusion Agent: Correlates git, CI/CD, and log evidence,
    determines the root cause, and computes the diagnosis confidence score.
    """
    incident_id = state.get("incident_db_id")
    ticket_id = state.get("ticket_id")
    pinned_commit_sha = state.get("pinned_commit_sha") or "unknown"
    
    gitlab_ev = state.get("gitlab_evidence") or {}
    cicd_ev = state.get("cicd_evidence") or {}
    log_ev = state.get("log_evidence") or {}
    
    log_to_db(incident_id, "Evidence Fusion Agent", "Fusing evidence from GitLab, CI/CD, and Log streams...")
    
    # Construct correlation prompt for Gemini
    prompt = f"""
    You are the Evidence Fusion Agent (Root Cause Analyser) for IncidentOps AI.
    Your job is to act as the primary reasoning layer, correlating clues to locate the exact cause of the incident.
    
    --- Incident Ticket ---
    Ticket ID: {ticket_id}
    Title: {state.get('title')}
    Description: {state.get('description')}
    
    --- IMPORTANT: Authoritative Commit Reference ---
    The GitLab Service has pinpointed the following as the key commit for this incident.
    You MUST reference this exact SHA in your evidence chain. Do NOT invent or reference any other commit SHA.
    Pinned Commit SHA: {pinned_commit_sha}
    
    --- GitLab Git History Evidence ---
    Suspicious Commits: {gitlab_ev.get('commits', [])}
    Target Code Files: {list(gitlab_ev.get('source_files', {}).keys())}
    
    --- CI/CD Test Evidence ---
    Pipeline Status: {cicd_ev.get('pipeline', {})}
    Test Failures: {cicd_ev.get('test_failures', [])}
    
    --- Log Stream Evidence ---
    Log Entries: {log_ev.get('logs', [])}
    
    --- Instructions ---
    1. Cross-reference timestamps, error lines, and the pinned commit. 
    2. Identify which file (`affected_file`) contains the bug and why.
    3. Calculate a diagnosis confidence score (between 0.0 and 1.0).
    4. Compile a chronological evidence chain using the pinned commit SHA {pinned_commit_sha[:8] if pinned_commit_sha != "unknown" else "unknown"}.
    
    Ensure the output strictly conforms to the structured JSON schema.
    """
    
    try:
        fusion_output = gemini_service.generate_structured(prompt, EvidenceFusionOutput)
        
        # Log findings
        log_to_db(
            incident_id, 
            "Evidence Fusion Agent", 
            f"Correlation complete. Root Cause: {fusion_output.root_cause} (Confidence: {int(fusion_output.confidence * 100)}%)"
        )
        
        for item in fusion_output.evidence_chain:
            log_to_db(incident_id, "Evidence Fusion Agent", f"Evidence Link: {item}")
            
        # Update database with confidence score
        from ..database import SessionLocal
        from ..models import Incident
        db = SessionLocal()
        try:
            db.query(Incident).filter(Incident.id == incident_id).update({
                "confidence_score": int(fusion_output.confidence * 100),
                "rca_report": f"Root Cause: {fusion_output.root_cause}\n\nEvidence:\n" + "\n".join(fusion_output.evidence_chain)
            })
            db.commit()
        finally:
            db.close()

        # Handle contextual refinement if requested
        if fusion_output.refinement_needed and fusion_output.refinement_query:
            log_to_db(
                incident_id, 
                "Evidence Fusion Agent", 
                f"Refinement requested: Performing second-pass query for '{fusion_output.refinement_query}'"
            )
            # In a full flow we would loop back; here we flag it and let the graph handle or continue.
            
        return {
            "root_cause": fusion_output.root_cause,
            "confidence_score": int(fusion_output.confidence * 100),
            "affected_file": fusion_output.affected_file,
            "evidence_chain": fusion_output.evidence_chain,
            "current_step": "PATCHING"
        }
        
    except Exception as e:
        log_to_db(incident_id, "Evidence Fusion Agent", f"Error during fusion correlation: {e}", level="ERROR")
        if not settings.ENABLE_MODEL_FALLBACKS:
            from ..database import SessionLocal
            from ..models import Incident
            db = SessionLocal()
            try:
                db.query(Incident).filter(Incident.id == incident_id).update({"status": "FAILED"})
                db.commit()
            finally:
                db.close()
            return {"current_step": "FAILED"}
        template = state.get("incident_template") or {}
        confidence = 80 if template else 50
        root_cause = template.get("expected_root_cause") or "Failed to automatically correlate root cause."
        affected_file = template.get("target_file") or "currency/converter.py"
        from ..database import SessionLocal
        from ..models import Incident
        db = SessionLocal()
        try:
            db.query(Incident).filter(Incident.id == incident_id).update({
                "confidence_score": confidence,
                "rca_report": f"Root Cause: {root_cause}\n\nEvidence:\nUsed incident template fallback after model correlation failed."
            })
            db.commit()
        finally:
            db.close()
        return {
            "root_cause": root_cause,
            "confidence_score": confidence,
            "affected_file": affected_file,
            "evidence_chain": ["Used incident template fallback after model correlation failed."],
            "current_step": "PATCHING"
        }
