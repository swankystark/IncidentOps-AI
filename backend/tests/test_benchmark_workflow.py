from types import SimpleNamespace

import pytest
import httpx

from app import database
from app.agents import fusion_agent
from app.agents import mr_agent
from app.services import gitlab as gitlab_module
from app.services.gemini import EvidenceFusionOutput, RCAOutput
from app.services.gitlab import GitLabService
from tools.benchmark import run_benchmark


class RetryGitLabService:
    def __init__(
        self,
        branch_results: list[bool],
        branch_exists_results: list[bool],
        mr_results: list[str | None],
    ) -> None:
        self.branch_results = iter(branch_results)
        self.branch_exists_results = iter(branch_exists_results)
        self.mr_results = iter(mr_results)
        self.branch_attempts = 0
        self.branch_exists_attempts = 0
        self.mr_attempts = 0

    async def create_branch(self, branch_name: str) -> bool:
        self.branch_attempts += 1
        return next(self.branch_results)

    async def get_file_content(self, file_path: str) -> str:
        return "old content"

    async def branch_exists(self, branch_name: str) -> bool:
        self.branch_exists_attempts += 1
        return next(self.branch_exists_results)

    async def commit_changes(
        self,
        branch_name: str,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> bool:
        return True

    async def create_merge_request(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
    ) -> str | None:
        self.mr_attempts += 1
        return next(self.mr_results)

    async def create_note_on_mr(self, mr_iid: int, body: str) -> bool:
        return True


def _mr_state() -> dict:
    return {
        "incident": {
            "incident_db_id": -1,
            "ticket_id": "INC-TEST",
            "title": "Test incident",
            "target_repo": "group/project",
            "target_branch": "main",
            "incident_template": {},
        },
        "fusion": {
            "affected_file": "src/example.py",
            "root_cause": "Test root cause",
            "confidence_score": 98,
        },
        "patch": {
            "target_content": "old content",
            "replacement_content": "new content",
            "patch_explanation": "Replace the broken content.",
        },
    }


@pytest.mark.asyncio
async def test_mr_agent_recovers_from_branch_race_and_mr_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RetryGitLabService(
        branch_results=[False, False, False],
        branch_exists_results=[False, False, True],
        mr_results=[None, "https://gitlab.com/group/project/-/merge_requests/44"],
    )
    monkeypatch.setattr(mr_agent.settings, "SKIP_MR_CREATION", False)
    monkeypatch.setattr(mr_agent, "log_to_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        mr_agent.GitLabService,
        "from_state",
        classmethod(lambda cls, state: service),
    )
    monkeypatch.setattr(
        mr_agent.llm_service,
        "generate_structured",
        lambda prompt, schema: RCAOutput(
            title="RCA",
            summary="Summary",
            root_cause_details="Root cause",
            remediation_details="Remediation",
            confidence_score=0.98,
        ),
    )

    result = await mr_agent.run_mr_agent(_mr_state())

    assert result["workflow"]["current_step"] == "COMPLETED"
    assert service.branch_attempts == 3
    assert service.branch_exists_attempts == 3
    assert service.mr_attempts == 2


@pytest.mark.asyncio
async def test_mr_agent_reconciles_existing_branch_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RetryGitLabService(
        branch_results=[False],
        branch_exists_results=[True],
        mr_results=["https://gitlab.com/group/project/-/merge_requests/45"],
    )
    monkeypatch.setattr(mr_agent.settings, "SKIP_MR_CREATION", False)
    monkeypatch.setattr(mr_agent, "log_to_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        mr_agent.GitLabService,
        "from_state",
        classmethod(lambda cls, state: service),
    )
    monkeypatch.setattr(
        mr_agent.llm_service,
        "generate_structured",
        lambda prompt, schema: RCAOutput(
            title="RCA",
            summary="Summary",
            root_cause_details="Root cause",
            remediation_details="Remediation",
            confidence_score=0.98,
        ),
    )

    result = await mr_agent.run_mr_agent(_mr_state())

    assert result["workflow"]["current_step"] == "COMPLETED"
    assert service.branch_attempts == 1
    assert service.branch_exists_attempts == 1
    assert service.mr_attempts == 1


@pytest.mark.asyncio
async def test_cached_workflow_runs_repository_context_before_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def run_node(state: dict, node_func) -> dict:
        calls.append(node_func.__name__)
        state.setdefault("workflow", {})["current_step"] = "READY"
        state.setdefault("validation", {})["validation_retry_count"] = 0
        return state

    monkeypatch.setattr(run_benchmark, "_run_node", run_node)
    monkeypatch.setattr(run_benchmark, "_load_cache", lambda *args: {"state": {}})
    monkeypatch.setattr(run_benchmark, "log_to_db", lambda *args, **kwargs: None)

    await run_benchmark._run_cached_workflow(
        {"workflow": {}, "validation": {}},
        incident_id=1,
        scenario_id="INC-101",
        target_repo="group/project",
        target_branch="main",
        benchmark_mode=True,
    )

    assert calls.index("run_repository_context") < calls.index("run_patch_agent")


def test_files_analyzed_counts_patch_target_and_repository_context() -> None:
    logs = [
        SimpleNamespace(
            agent_name="Patch Generation Agent",
            message="Drafting code fix for file 'auth/session_service.py'...",
        ),
        SimpleNamespace(
            agent_name="Repository Context",
            message="Files analyzed: 3; primary='auth/session_service.py'",
        ),
    ]

    assert database._count_files_analyzed(logs) == 3


@pytest.mark.asyncio
async def test_fusion_agent_prefers_dependency_template_target_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fusion_agent, "log_to_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        fusion_agent.llm_service,
        "generate_structured",
        lambda prompt, schema: EvidenceFusionOutput(
            root_cause="Dependency mismatch",
            confidence=0.98,
            affected_file="billing/tax_engine.py",
            evidence_chain=["billing log", "requirements pin"],
            refinement_needed=False,
            refinement_query="",
        ),
    )

    state = {
        "incident": {
            "incident_db_id": -1,
            "ticket_id": "INC-103-TEST",
            "title": "Dependency mismatch on JSON serialization",
            "description": "Dependency mismatch",
            "incident_template": {
                "validation": "dependency_validator",
                "target_file": "requirements.txt",
            },
        },
        "retrieval": {
            "gitlab_evidence": {"source_files": {"requirements.txt": "pydantic==1.9.0"}},
            "cicd_evidence": {"pipeline": {}},
            "log_evidence": {"logs": []},
        },
        "fusion": {"pinned_commit_sha": "abc123"},
    }

    result = await fusion_agent.run_fusion_agent(state)

    assert result["fusion"]["affected_file"] == "requirements.txt"


@pytest.mark.asyncio
async def test_gitlab_reconciles_existing_mr_after_transient_non_conflict_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(self, status_code: int, payload: list[dict] | dict | None = None) -> None:
            self.status_code = status_code
            self._payload = payload

        def json(self) -> list[dict] | dict:
            assert self._payload is not None
            return self._payload

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url, headers, json) -> FakeResponse:
            return FakeResponse(503, {})

        async def get(self, url, headers, params) -> FakeResponse:
            return FakeResponse(200, [{"web_url": "https://gitlab.com/group/project/-/merge_requests/44"}])

    monkeypatch.setattr(gitlab_module.httpx, "AsyncClient", FakeClient)

    service = GitLabService(project_path="group/project", target_branch="main", target_app_path=".")
    result = await service.create_merge_request_real(
        source_branch="incidentops/fix-inc-1",
        target_branch="main",
        title="Resolve incident",
        description="body",
    )

    assert result == "https://gitlab.com/group/project/-/merge_requests/44"
