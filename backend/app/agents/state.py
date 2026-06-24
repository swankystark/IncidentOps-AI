from typing import TypedDict, List, Dict, Any, Optional, Annotated

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    a_dict = a if a is not None else {}
    b_dict = b if b is not None else {}
    return {**a_dict, **b_dict}

class AgentState(TypedDict, total=False):
    # ---------------------------------------------------------
    # NEW NESTED GROUPS (Phase 6 Migration)
    # ---------------------------------------------------------
    incident: Annotated[Dict[str, Any], merge_dicts]
    retrieval: Annotated[Dict[str, Any], merge_dicts]
    fusion: Annotated[Dict[str, Any], merge_dicts]
    repo_context: Annotated[Dict[str, Any], merge_dicts]
    patch: Annotated[Dict[str, Any], merge_dicts]
    validation: Annotated[Dict[str, Any], merge_dicts]
    delivery: Annotated[Dict[str, Any], merge_dicts]
    workflow: Annotated[Dict[str, Any], merge_dicts]
    metrics: Annotated[Dict[str, Any], merge_dicts]

    # Workflow recovery: reason for failure if quota/rate-limit caused a halt
    failure_reason: Optional[str]
