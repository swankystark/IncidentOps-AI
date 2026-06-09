from ..database import log_to_db
from ..services.gitlab import GitLabService
from ..validation_strategies import get_validation_strategy
from .state import AgentState


async def run_validation(state: AgentState) -> dict:
    """
    Validation Service: delegates incident-specific checks to a registered
    validation strategy selected by the incident template.
    """
    incident_id = state.get("incident_db_id")
    template = state.get("incident_template") or {}
    affected_file = state.get("affected_file") or template.get("target_file") or "unknown"
    retry_count = state.get("validation_retry_count", 0)
    strategy_name = template.get("validation") or "generic_pytest"

    log_to_db(incident_id, "Validation Service", f"Running '{strategy_name}' for '{affected_file}'...")

    try:
        gitlab_service = GitLabService.from_state(state)
        strategy = get_validation_strategy(strategy_name)
        result = await strategy.validate(state, gitlab_service)
        logs = result.get("logs", "")

        if result.get("passed"):
            log_to_db(incident_id, "Validation Service", "Validation PASSED. All tests succeeded! (Remediation is safe).")
            return {
                "validation_passed": True,
                "validation_logs": logs,
                "current_step": "CREATING_MR",
            }

        log_to_db(
            incident_id,
            "Validation Service",
            f"Validation FAILED. Test logs:\n{logs}",
            level="WARNING",
        )
        if retry_count < 1:
            log_to_db(incident_id, "Validation Service", "Triggering patch generation retry loop (Attempt 1/1).")
            return {
                "validation_passed": False,
                "validation_logs": logs,
                "validation_retry_count": retry_count + 1,
                "current_step": "PATCHING",
            }

        log_to_db(incident_id, "Validation Service", "Maximum retry limit exceeded. Proceeding to MR with warnings.", level="ERROR")
        return {
            "validation_passed": False,
            "validation_logs": logs,
            "current_step": "CREATING_MR",
        }

    except Exception as e:
        log_to_db(incident_id, "Validation Service", f"Error during validation strategy execution: {e}.", level="ERROR")
        return {
            "validation_passed": False,
            "validation_logs": str(e),
            "validation_retry_count": retry_count + 1,
            "current_step": "FAILED",
        }
