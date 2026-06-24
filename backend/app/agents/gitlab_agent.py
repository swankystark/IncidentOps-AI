from ..services.gitlab import GitLabService
from ..database import log_to_db
from .state import AgentState

async def run_gitlab_service(state: AgentState) -> dict:
    """
    GitLab Service: Searches commits, pulls history, and inspects files
    related to the suspected module in the shared context.
    """
    incident = state.get("incident", {})
    incident_id = incident.get("incident_db_id")
    context = state.get("retrieval", {}).get("shared_context", {})
    template = incident.get("incident_template", {})
    gitlab_service = GitLabService.from_state(state)
    
    module = context.get("suspected_module") or template.get("module") or "currency"
    signals = context.get("priority_signals") or template.get("priority_signals") or []
    
    log_to_db(incident_id, "GitLab Service", f"Scanning repository history for signals: {signals}")
    
    evidence = {}
    try:
        # Search commits matching priority signals
        search_query = signals[0] if signals else module
        commits = await gitlab_service.search_commits(search_query)
        
        suspicious_commits = []
        for c in commits:
            log_to_db(incident_id, "GitLab Service", f"Found suspicious commit: {c.get('short_id')} - '{c.get('title')}' by {c.get('author_name')}")
            suspicious_commits.append({
                "sha": c.get("id"),
                "short_id": c.get("short_id"),
                "title": c.get("title"),
                "author": c.get("author_name"),
                "message": c.get("message"),
                "created_at": c.get("created_at")
            })
            
        evidence["commits"] = suspicious_commits
 
        # Pin the most relevant commit SHA for consistent attribution across all agents
        # Prefer commits that explicitly mention the suspected module in their title
        pinned_commit = None
        for c in suspicious_commits:
            if module.lower() in (c.get("title") or "").lower():
                pinned_commit = c
                break
        if not pinned_commit and suspicious_commits:
            pinned_commit = suspicious_commits[0]
        pinned_sha = pinned_commit.get("sha") if pinned_commit else None
        if pinned_sha:
            log_to_db(incident_id, "GitLab Service", f"Pinned key commit: {pinned_sha[:8]} — '{pinned_commit.get('title')}'")
        
        # Read relevant files to capture current source state
        target_file = template.get("target_file") or (f"{module}/converter.py" if module == "currency" else f"{module}/service.py")
        source_code = await gitlab_service.get_file_content(target_file)
        
        if source_code:
            log_to_db(incident_id, "GitLab Service", f"Successfully retrieved source code for review: '{target_file}'")
            evidence["source_files"] = {
                target_file: source_code
            }
        else:
            log_to_db(incident_id, "GitLab Service", f"Warning: Could not fetch source code for {target_file}", level="WARNING")
            evidence["source_files"] = {}
            
        return {
            "retrieval": {"gitlab_evidence": evidence},
            "fusion": {"pinned_commit_sha": pinned_sha}
        }
        
    except Exception as e:
        log_to_db(incident_id, "GitLab Service", f"Error collecting git evidence: {e}", level="ERROR")
        return {
            "retrieval": {"gitlab_evidence": {"error": str(e)}},
            "fusion": {"pinned_commit_sha": None}
        }
