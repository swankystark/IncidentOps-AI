from app.agents.graph import compiled_graph


def test_parallel_evidence_retrieval_topology() -> None:
    edges = {
        (edge.source, edge.target)
        for edge in compiled_graph.get_graph().edges
        if not edge.conditional
    }

    assert ("planner", "log_service") in edges
    assert ("planner", "gitlab_service") in edges
    assert ("gitlab_service", "cicd_service") in edges
    assert ("log_service", "evidence_fusion") in edges
    assert ("cicd_service", "evidence_fusion") in edges
    assert ("evidence_fusion", "repository_context") in edges
    assert ("repository_context", "patch_generation") in edges

    assert ("log_service", "gitlab_service") not in edges
    assert ("planner", "cicd_service") not in edges
