import anyio
import httpx

from ..services.gitlab import GitLabService
from ..services.gemini import llm_service, RCAOutput
from ..database import log_to_db
from ..config import settings
from .state import AgentState

async def run_mr_agent(state: AgentState) -> dict:
    """
    MR & RCA Creation Agent: Pushes the patched file to GitLab,
    opens a Merge Request, and comments a detailed Root Cause Analysis (RCA).
    """
    incident = state.get("incident", {})
    incident_id = incident.get("incident_db_id")
    ticket_id = incident.get("ticket_id")
    template = incident.get("incident_template", {})

    fusion = state.get("fusion", {})
    affected_file = fusion.get("affected_file") or template.get("target_file") or "currency/converter.py"
    root_cause = fusion.get("root_cause")
    confidence_score = fusion.get("confidence_score") or 90

    patch_group = state.get("patch", {})
    target_content = patch_group.get("target_content")
    replacement_content = patch_group.get("replacement_content")
    patch_explanation = patch_group.get("patch_explanation") or ""

    target_repo = incident.get("target_repo") or "unknown"
    title = incident.get("title")
    target_branch = incident.get("target_branch") or "main"

    # Skip real MR creation in benchmark mode
    if settings.SKIP_MR_CREATION:
        log_to_db(incident_id, "MR & RCA Agent", "SKIP_MR_CREATION enabled - generating synthetic MR")
        import uuid
        synthetic_mr_url = f"https://gitlab.com/{target_repo}/-/merge_requests/SIM-{uuid.uuid4().hex[:8]}"
        rca_markdown = f"# Simulated RCA for {ticket_id}\n\nRoot Cause: {root_cause}\n\nPatch: {patch_explanation}"
        return {
            "delivery": {
                "gitlab_mr_url": synthetic_mr_url,
                "rca_report": rca_markdown
            },
            "workflow": {"current_step": "COMPLETED"}
        }
    
    log_to_db(incident_id, "MR & RCA Agent", "Generating Root Cause Analysis (RCA) report...")
    if not target_content or replacement_content is None:
        log_to_db(incident_id, "MR & RCA Agent", "Cannot create MR: patch content is missing.", level="ERROR")
        return {"workflow": {"current_step": "FAILED"}}
    
    # 1. Generate the RCA report using Gemini
    rca_prompt = f"""
    You are the Lead SRE and incident responder for IncidentOps AI.
    Generate a professional, detailed, markdown-formatted Root Cause Analysis (RCA) report.
    
    Incident Ticket: {ticket_id} - {title}
    Root Cause: {root_cause}
    Confidence Score: {confidence_score}%
    Affected File: {affected_file}
    
    The output must strictly conform to the RCAOutput structured schema.
    """
    
    try:
        try:
            rca_output = llm_service.generate_structured(rca_prompt, RCAOutput)
        except Exception as e:
            if not settings.ENABLE_MODEL_FALLBACKS:
                raise e
            log_to_db(incident_id, "MR & RCA Agent", f"RCA model generation failed; using deterministic fallback RCA. Error: {e}", level="WARNING")
            rca_output = RCAOutput(
                title=f"Root Cause Analysis Report for {ticket_id}",
                summary=f"IncidentOps AI identified and patched {affected_file} for incident {ticket_id}.",
                root_cause_details=root_cause or "Root cause was derived from collected GitLab, CI/CD, and runtime log evidence.",
                remediation_details=patch_explanation or "The generated patch updates the affected source or dependency declaration and was passed to validation.",
                confidence_score=(confidence_score / 100) if confidence_score > 1 else confidence_score,
            )
        
        rca_markdown = f"""# {rca_output.title}

## Executive Summary
{rca_output.summary}

## Root Cause Analysis
* **Affected File:** `{affected_file}`
* **Confidence Level:** {rca_output.confidence_score * 100 if rca_output.confidence_score <= 1.0 else rca_output.confidence_score}%
* **Details:**
{rca_output.root_cause_details}

## Remediation Details
{rca_output.remediation_details}

---
*Report generated autonomously by IncidentOps AI.*
"""
        
        # 2. Push code changes and create Merge Request on GitLab
        gitlab_service = GitLabService.from_state(state)
        import uuid
        branch_name = f"incidentops/fix-{ticket_id.lower()}-{incident_id}-{uuid.uuid4().hex[:6]}"
        log_to_db(incident_id, "MR & RCA Agent", f"Creating GitLab branch '{branch_name}'...")
        
        # Branch creation
        branch_created = False
        branch_error = "GitLab returned a non-success response"
        for attempt in range(1, 4):
            try:
                branch_created = await gitlab_service.create_branch(branch_name)
                if not branch_created and await gitlab_service.branch_exists(branch_name):
                    branch_created = True
            except httpx.HTTPError as exc:
                branch_error = str(exc)
                branch_created = await gitlab_service.branch_exists(branch_name)
            if branch_created:
                break
            if attempt < 3:
                await anyio.sleep(0.5 * attempt)
        if not branch_created:
            raise RuntimeError(
                f"Failed to create GitLab branch '{branch_name}' after 3 attempts: {branch_error}."
            )
        
        # Apply fix & commit
        # Fetch the original code first to write the final content
        original_code = await gitlab_service.get_file_content(affected_file)
        fixed_code = original_code.replace(target_content, replacement_content)
        
        log_to_db(incident_id, "MR & RCA Agent", f"Committing patch to '{affected_file}' on branch '{branch_name}'...")
        committed = False
        commit_error = "GitLab returned a non-success response"
        for attempt in range(1, 4):
            try:
                committed = await gitlab_service.commit_changes(
                    branch_name=branch_name,
                    file_path=affected_file,
                    content=fixed_code,
                    commit_message=f"fix: Resolve incident {ticket_id} ({rca_output.title})"
                )
            except httpx.HTTPError as exc:
                commit_error = str(exc)
                committed = False
            if committed:
                break
            if attempt < 3:
                await anyio.sleep(0.5 * attempt)
        if not committed:
            raise RuntimeError(
                f"Failed to commit patch to '{affected_file}' on branch '{branch_name}' "
                f"after 3 attempts: {commit_error}."
            )
        
        # Create MR
        mr_title = f"Resolve Incident {ticket_id}: {rca_output.title}"
        mr_desc = f"""### Autonomous Incident Remediation
This Merge Request has been opened automatically by **IncidentOps AI** to resolve incident **{ticket_id}**.

#### Summary of Fix
{rca_output.summary}

#### RCA Report Reference
The complete Root Cause Analysis report has been posted as a comment on this MR.
"""
        log_to_db(incident_id, "MR & RCA Agent", f"Opening GitLab Merge Request: '{mr_title}'...")
        mr_url = None
        mr_error = "GitLab returned a non-success response"
        for attempt in range(1, 4):
            try:
                mr_url = await gitlab_service.create_merge_request(
                    source_branch=branch_name,
                    target_branch=target_branch,
                    title=mr_title,
                    description=mr_desc
                )
            except httpx.HTTPError as exc:
                mr_error = str(exc)
            if mr_url:
                break
            if attempt < 3:
                await anyio.sleep(0.5 * attempt)
        if not mr_url:
            raise RuntimeError(
                f"Failed to create or locate GitLab Merge Request for branch '{branch_name}' "
                f"after 3 attempts: {mr_error}."
            )
        
        log_to_db(incident_id, "MR & RCA Agent", f"Merge Request created successfully! URL: {mr_url}")
        
        # Post RCA report as MR note/comment if MR IID can be extracted
        if mr_url and "/merge_requests/" in mr_url:
            try:
                mr_iid = int(mr_url.split("/merge_requests/")[-1].split("?")[0])
                await gitlab_service.create_note_on_mr(mr_iid, rca_markdown)
                log_to_db(incident_id, "MR & RCA Agent", f"Posted RCA report as a comment on MR #{mr_iid}.")
            except Exception as e:
                print(f"Failed to post note on MR: {e}")
                
        # 3. Update SQLite Incident record
        from ..database import SessionLocal
        from ..models import Incident
        db = SessionLocal()
        try:
            db.query(Incident).filter(Incident.id == incident_id).update({
                "status": "RESOLVED",
                "gitlab_mr_url": mr_url,
                "rca_report": rca_markdown
            })
            db.commit()
        finally:
            db.close()
            
        log_to_db(incident_id, "MR & RCA Agent", "Incident investigation and remediation flow COMPLETED.", level="INFO")
        
        return {
            "delivery": {
                "gitlab_mr_url": mr_url,
                "rca_report": rca_markdown
            },
            "workflow": {"current_step": "COMPLETED"}
        }
        
    except Exception as e:
        log_to_db(incident_id, "MR & RCA Agent", f"Error creating MR/RCA: {e}", level="ERROR")
        return {
            "workflow": {"current_step": "FAILED"}
        }
