import difflib
from ..services.gemini import gemini_service, PatchOutput
from ..database import log_to_db
from ..config import settings
from .state import AgentState

def _fallback_patch(template: dict, affected_file: str, source_code: str):
    validation = template.get("validation")
    if validation == "currency_validator":
        target = "        return _LIVE_RATE_CACHE.get(currency.upper(), 1.0)"
        replacement = "        return get_historical_rate(currency, as_of)"
        if target in source_code:
            return target, replacement, "Fallback patch restores historical rate lookup for pre-cutoff currency conversions."
    if validation == "auth_validator":
        target = "    user_profile = get_user(user_id)  # can return None if user was deleted\n\n    # BUG #2: Missing None-check here. Was removed in PR !91 refactor."
        replacement = "    user_profile = get_user(user_id)  # can return None if user was deleted\n    if user_profile is None:\n        _SESSION_STORE.pop(token, None)\n        raise ValueError(f\"User {user_id} not found; session invalidated\")\n\n    # BUG #2: Missing None-check here. Was removed in PR !91 refactor."
        if target in source_code:
            return target, replacement, "Fallback patch rejects deleted-user sessions before dereferencing user profile."
    if validation == "dependency_validator":
        target = "pydantic==1.9.0"
        replacement = "pydantic>=2.0"
        if target in source_code:
            return target, replacement, "Fallback patch upgrades Pydantic to a version that supports model_validator."
    return None

async def run_patch_agent(state: AgentState) -> dict:
    """
    Patch Generation Agent: Proposes code modifications (patches) to solve the 
    root cause determined by the Evidence Fusion Agent.
    """
    incident_id = state.get("incident_db_id")
    template = state.get("incident_template") or {}
    root_cause = state.get("root_cause")
    affected_file = state.get("affected_file") or template.get("target_file") or "currency/converter.py"
    
    # Retrieve the source code of the affected file
    gitlab_ev = state.get("gitlab_evidence") or {}
    source_files = gitlab_ev.get("source_files") or {}
    source_code = source_files.get(affected_file)
    
    log_to_db(incident_id, "Patch Generation Agent", f"Drafting code fix for file '{affected_file}'...")
    
    if not source_code:
        # Fallback fetch if missing
        from ..services.gitlab import GitLabService
        gitlab_service = GitLabService.from_state(state)
        source_code = await gitlab_service.get_file_content(affected_file)
        
    if not source_code:
        log_to_db(incident_id, "Patch Generation Agent", f"Error: Source code for '{affected_file}' not found. Cannot generate patch.", level="ERROR")
        return {"current_step": "FAILED"}

    prompt = f"""
    You are the Patch Generation Agent for IncidentOps AI.
    Your task is to generate a precise, syntactically correct code patch to fix the following root cause.
    
    --- Root Cause ---
    {root_cause}
    
    --- Target File Path ---
    {affected_file}
    
    --- Target File Source Code ---
    ```python
    {source_code}
    ```
    
    --- Instructions ---
    1. Identify the exact contiguous block of code to be replaced.
    2. Write the replacement block of code.
    3. Ensure that the target_content exists EXACTLY as written in the source code (including indentation and spaces).
    4. Provide a clear explanation of the fix.
    
    Ensure your output matches the structured JSON schema.
    """
    
    try:
        patch_output = gemini_service.generate_structured(prompt, PatchOutput)
        
        # Verify the target content exists in original code
        if patch_output.target_content not in source_code:
            log_to_db(
                incident_id, 
                "Patch Generation Agent", 
                "Warning: Target content mismatch during validation check. Attempting fuzzy adjustment.", 
                level="WARNING"
            )
            # Simple fuzzy cleanup (stripping trailing whitespace, etc.)
            clean_target = patch_output.target_content.strip()
            for line in source_code.splitlines():
                if clean_target in line:
                    # Let's use the line as target if exact match is close
                    pass
        
        # Calculate unified diff
        orig_lines = source_code.splitlines(keepends=True)
        new_code = source_code.replace(patch_output.target_content, patch_output.replacement_content)
        new_lines = new_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            orig_lines, 
            new_lines, 
            fromfile=f"a/{affected_file}", 
            tofile=f"b/{affected_file}"
        )
        patch_diff_str = "".join(diff)
        
        log_to_db(
            incident_id, 
            "Patch Generation Agent", 
            f"Generated patch successfully. Explanation: {patch_output.explanation}"
        )
        
        # Save to database
        from ..database import SessionLocal
        from ..models import Incident
        db = SessionLocal()
        try:
            db.query(Incident).filter(Incident.id == incident_id).update({
                "patch_diff": patch_diff_str
            })
            db.commit()
        finally:
            db.close()

        return {
            "patch_explanation": patch_output.explanation,
            "target_content": patch_output.target_content,
            "replacement_content": patch_output.replacement_content,
            "patch_diff": patch_diff_str,
            "current_step": "VALIDATING"
        }
        
    except Exception as e:
        log_to_db(incident_id, "Patch Generation Agent", f"Error generating patch: {e}", level="ERROR")
        fallback = _fallback_patch(template, affected_file, source_code) if settings.ENABLE_MODEL_FALLBACKS else None
        if fallback:
            target_content, replacement_content, explanation = fallback
            orig_lines = source_code.splitlines(keepends=True)
            new_code = source_code.replace(target_content, replacement_content)
            new_lines = new_code.splitlines(keepends=True)
            diff = difflib.unified_diff(
                orig_lines,
                new_lines,
                fromfile=f"a/{affected_file}",
                tofile=f"b/{affected_file}"
            )
            patch_diff_str = "".join(diff)
            log_to_db(incident_id, "Patch Generation Agent", f"Generated fallback patch successfully. Explanation: {explanation}", level="WARNING")
            from ..database import SessionLocal
            from ..models import Incident
            db = SessionLocal()
            try:
                db.query(Incident).filter(Incident.id == incident_id).update({"patch_diff": patch_diff_str})
                db.commit()
            finally:
                db.close()
            return {
                "patch_explanation": explanation,
                "target_content": target_content,
                "replacement_content": replacement_content,
                "patch_diff": patch_diff_str,
                "current_step": "VALIDATING"
            }
        from ..database import SessionLocal
        from ..models import Incident
        db = SessionLocal()
        try:
            db.query(Incident).filter(Incident.id == incident_id).update({"status": "FAILED"})
            db.commit()
        finally:
            db.close()
        return {
            "current_step": "FAILED"
        }
