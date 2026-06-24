import difflib
from ..services.gemini import llm_service, PatchOutput
from ..database import log_to_db
from ..config import settings
from .state import AgentState
from ..services.code_targeting import CodeTargetingService

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
    incident = state.get("incident", {})
    incident_id = incident.get("incident_db_id")
    template = incident.get("incident_template", {})
    fusion = state.get("fusion", {})
    root_cause = fusion.get("root_cause")
    affected_file = fusion.get("affected_file") or template.get("target_file") or "currency/converter.py"
    
    # Retrieve the source code of the affected file
    retrieval = state.get("retrieval", {})
    gitlab_ev = retrieval.get("gitlab_evidence") or state.get("gitlab_evidence") or {}
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

    log_evidence_dict = retrieval.get("log_evidence", {})
    logs = log_evidence_dict.get("logs", "")
    if isinstance(logs, list):
        logs = "\n".join(logs)
    
    target_info = CodeTargetingService.target_code(source_code, affected_file, root_cause, logs)
    target_content = target_info.get("target_content", source_code)
    start_line = target_info.get("start_line", 1)
    end_line = target_info.get("end_line", len(source_code.splitlines()))
    target_func = target_info.get("function_name")
    
    func_str = f" in function `{target_func}`" if target_func else ""
    log_to_db(incident_id, "Patch Generation Agent", f"Targeting code lines {start_line}-{end_line}{func_str} via Code Targeting Service.")

    # Get repository context for richer patch generation
    repo_context = state.get("repo_context") or {}
    related_files = repo_context.get("related_files", [])
    import_deps = repo_context.get("import_dependencies", [])
    test_files = repo_context.get("test_files", [])
    recent_commits = repo_context.get("recent_commits", [])
    supporting_context = repo_context.get("supporting_context", {})

    context_parts = []
    if related_files:
        context_parts.append(f"--- Related Files ---\n{', '.join(related_files)}")
    if import_deps:
        context_parts.append(f"--- Import Dependencies ---\n{', '.join(import_deps)}")
    if test_files:
        context_parts.append(f"--- Test Files ---\n{', '.join(test_files)}")
    if recent_commits:
        commits_str = "\n".join([f"  {c.get('sha', '')[:8]}: {c.get('title', '')}" for c in recent_commits[:3]])
        context_parts.append(f"--- Recent Commits ---\n{commits_str}")
    context_str = "\n\n".join(context_parts) if context_parts else "No additional repository context available."

    prompt = f"""
    You are the Patch Generation Agent for IncidentOps AI.
    Your task is to generate a precise, syntactically correct code patch to fix the following root cause.
    
    --- Root Cause ---
    {root_cause}
    
    --- Target File Path ---
    {affected_file}
    
    --- Exact Code Block to Replace ---
    (Lines {start_line} to {end_line})
    ```python
    {target_content}
    ```
    
    {context_str}
    
    --- Instructions ---
    1. Write the replacement block of code that completely replaces the given code block. Do NOT include the surrounding lines.
    2. Provide a clear explanation of the fix.
    
    Ensure your output matches the structured JSON schema.
    """
    
    try:
        patch_output = llm_service.generate_structured(prompt, PatchOutput)
        
        # Calculate unified diff
        orig_lines = source_code.splitlines(keepends=True)
        replacement_lines = patch_output.replacement_content.splitlines(keepends=True)
        if replacement_lines and not replacement_lines[-1].endswith("\n"):
            replacement_lines[-1] += "\n"
            
        new_lines = orig_lines[:start_line - 1] + replacement_lines + orig_lines[end_line:]
        
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
            "target_content": target_content,
            "replacement_content": patch_output.replacement_content,
            "patch": {
                "patch_explanation": patch_output.explanation,
                "target_content": target_content,
                "replacement_content": patch_output.replacement_content,
                "patch_diff": patch_diff_str
            },
            "workflow": {"current_step": "VALIDATING"}
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
                "target_content": target_content,
                "replacement_content": replacement_content,
                "patch": {
                    "patch_explanation": explanation,
                    "target_content": target_content,
                    "replacement_content": replacement_content,
                    "patch_diff": patch_diff_str
                },
                "workflow": {"current_step": "VALIDATING"}
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
            "workflow": {"current_step": "FAILED"}
        }
