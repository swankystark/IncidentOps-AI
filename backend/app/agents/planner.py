from ..services.gemini import llm_service, PlannerOutput
from ..database import log_to_db
from .state import AgentState

async def run_planner(state: AgentState) -> dict:
    """
    Planner Agent: Analyzes the incident ticket, determines suspected modules,
    and initializes the Shared Investigation Context.
    """
    incident = state.get("incident", {})
    incident_id = incident.get("incident_db_id")
    ticket_id = incident.get("ticket_id")
    title = incident.get("title")
    description = incident.get("description")
    template = incident.get("incident_template") or {}
    
    log_to_db(incident_id, "Planner Agent", f"Initializing planning phase for ticket {ticket_id}: '{title}'")
    
    prompt = f"""
    You are the Planner Agent for IncidentOps AI, an autonomous DevSecOps incident response system.
    Your task is to analyze the incoming incident ticket and formulate a shared investigation context.
    
    Ticket ID: {ticket_id}
    Title: {title}
    Description: {description}
    
    Determine:
    1. The name of the single suspected module/directory (e.g., 'currency', 'auth', 'reports', 'billing').
    2. The type of error (e.g., 'logic regression', 'null pointer', 'dependency mismatch').
    3. A realistic time window for repository history checks.
    4. Relevant keywords or files to guide parallel retrieval agents.
    
    Ensure your output matches the structured JSON schema.
    """
    
    try:
        # Generate structured response from Gemini
        planner_output = llm_service.generate_structured(prompt, PlannerOutput)
        
        context_dict = {
            "suspected_module": template.get("module") or planner_output.suspected_module,
            "suspected_error_type": template.get("error_type") or planner_output.suspected_error_type,
            "time_window": planner_output.time_window,
            "priority_signals": template.get("priority_signals") or planner_output.priority_signals
        }
        
        log_to_db(
            incident_id, 
            "Planner Agent", 
            f"Planning complete. Suspected module: '{planner_output.suspected_module}' ({planner_output.suspected_error_type})."
        )
        
        return {
            "retrieval": {"shared_context": context_dict},
            "workflow": {"current_step": "RETRIEVING"}
        }
    except Exception as e:
        log_to_db(incident_id, "Planner Agent", f"Error during planning: {e}", level="ERROR")
        # Fallback context in case of error (defaults to currency conversion scenario)
        fallback_context = {
            "suspected_module": template.get("module", "currency"),
            "suspected_error_type": template.get("error_type", "logic regression"),
            "time_window": "last 7 days",
            "priority_signals": template.get("priority_signals", ["currency", "conversion", "reports", "exchange rate"])
        }
        return {
            "retrieval": {"shared_context": fallback_context},
            "workflow": {"current_step": "RETRIEVING"}
        }
