from langgraph.graph import StateGraph, END
from .state import AgentState
from .planner import run_planner
from .gitlab_agent import run_gitlab_service
from .cicd_agent import run_cicd_service
from .log_agent import run_log_service
from .fusion_agent import run_fusion_agent
from .repository_context import run_repository_context
from .patch_agent import run_patch_agent
from .validation_agent import run_validation
from .mr_agent import run_mr_agent

def create_workflow_graph() -> StateGraph:
    """Builds and compiles the IncidentOps AI LangGraph workflow graph."""
    workflow = StateGraph(AgentState)
    
    # 1. Define Node Executors
    workflow.add_node("planner", run_planner)
    workflow.add_node("gitlab_service", run_gitlab_service)
    workflow.add_node("cicd_service", run_cicd_service)
    workflow.add_node("log_service", run_log_service)
    workflow.add_node("evidence_fusion", run_fusion_agent)
    workflow.add_node("repository_context", run_repository_context)
    workflow.add_node("patch_generation", run_patch_agent)
    workflow.add_node("validation_service", run_validation)
    workflow.add_node("mr_creation", run_mr_agent)
    
    # 2. Define Entry Point
    workflow.set_entry_point("planner")
    
    # 3. Define Retrieval Flow
    # Log retrieval and GitLab attribution are independent after planning.
    # CI/CD remains downstream of GitLab so pipeline selection can use the
    # pinned commit and GitLab evidence before the evidence-fusion fan-in.
    workflow.add_edge("planner", "log_service")
    workflow.add_edge("planner", "gitlab_service")
    workflow.add_edge("gitlab_service", "cicd_service")
    workflow.add_edge(["log_service", "cicd_service"], "evidence_fusion")
    
    # 5. Define Centralized Reasoning to Sequential Patching Pipeline
    workflow.add_edge("evidence_fusion", "repository_context")
    workflow.add_edge("repository_context", "patch_generation")
    def route_after_patch(state: AgentState) -> str:
        current_step = state.get("workflow", {}).get("current_step")
        if current_step == "FAILED":
            return "end"
        return "validation_service"

    workflow.add_conditional_edges(
        "patch_generation",
        route_after_patch,
        {
            "validation_service": "validation_service",
            "end": END
        }
    )
    
    # 6. Define Conditional Edge for Validation & Retry Loop (exactly 1 retry)
    def route_after_validation(state: AgentState) -> str:
        current_step = state.get("workflow", {}).get("current_step")
        if current_step == "FAILED":
            return "end"
        
        validation = state.get("validation", {})
        passed = validation.get("validation_passed")
        retry_count = validation.get("validation_retry_count", 0)
        
        # Route back to patch generation on test failure, up to 1 retry
        if not passed and retry_count <= 1 and current_step == "PATCHING":
            return "patch_generation"
        return "mr_creation"
        
    workflow.add_conditional_edges(
        "validation_service",
        route_after_validation,
        {
            "patch_generation": "patch_generation",
            "mr_creation": "mr_creation",
            "end": END
        }
    )
    
    # 7. Close workflow loop
    workflow.add_edge("mr_creation", END)
    
    return workflow.compile()

# Instantiated compiled runnable graph
compiled_graph = create_workflow_graph()
