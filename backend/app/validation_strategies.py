import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .config import resolve_project_path
from .incident_registry import target_app_path_for
from .services.gitlab import GitLabService


class ValidationStrategy:
    name = "base"

    async def validate(self, state: Dict[str, Any], gitlab_service: GitLabService) -> Dict[str, Any]:
        raise NotImplementedError


class PytestValidationStrategy(ValidationStrategy):
    name = "generic_pytest"

    async def validate(self, state: Dict[str, Any], gitlab_service: GitLabService) -> Dict[str, Any]:
        incident = state.get("incident") or {}
        template = state.get("incident_template") or incident.get("incident_template") or {}
        affected_file = state.get("affected_file") or template.get("target_file")
        patch_state = state.get("patch") or {}
        target_content = state.get("target_content") or patch_state.get("target_content")
        replacement_content = state.get("replacement_content") or patch_state.get("replacement_content")
        test_target = template.get("test_target")

        if not affected_file or not target_content or replacement_content is None or not test_target:
            return {
                "passed": False,
                "logs": "Validation template is missing affected_file, patch content, or test_target.",
            }

        original_code = await self._read_source(gitlab_service, affected_file)
        if not original_code:
            return {"passed": False, "logs": f"Unable to retrieve source for {affected_file}."}

        patched_code = original_code.replace(target_content, replacement_content)
        if patched_code == original_code:
            return {"passed": False, "logs": "Patch target content was not found in source."}

        with tempfile.TemporaryDirectory(prefix="incidentops-validate-") as tmp:
            workspace = Path(tmp)
            self._write_file(workspace, affected_file, patched_code)

            for support_path in template.get("supporting_files", []):
                support_code = await self._read_source(gitlab_service, support_path)
                if support_code:
                    self._write_file(workspace, support_path, support_code)

            test_file = test_target.split("::")[0]
            test_code = await self._read_source(gitlab_service, test_file)
            if not test_code:
                return {"passed": False, "logs": f"Unable to retrieve test file {test_file}."}
            self._write_file(workspace, test_file, test_code)

            pytest_target = test_target
            if "::" in test_target:
                file_part, case_part = test_target.split("::", 1)
                pytest_target = f"{file_part}::{case_part}"

            pytest_path = str(resolve_project_path(os.path.join("venv", "Scripts", "pytest.exe")))
            if not os.path.exists(pytest_path):
                pytest_path = "pytest"

            env = os.environ.copy()
            env["PYTHONPATH"] = str(workspace)
            try:
                result = subprocess.run(
                    [pytest_path, pytest_target, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    env=env,
                    cwd=str(workspace),
                )
            except subprocess.TimeoutExpired as exc:
                return {
                    "passed": False,
                    "logs": f"Validation command timed out after {exc.timeout} seconds.",
                }
            return {
                "passed": result.returncode == 0,
                "logs": (result.stdout or "") + (result.stderr or ""),
            }

    async def _read_source(self, gitlab_service: GitLabService, file_path: str) -> str:
        remote_content = await gitlab_service.get_file_content(file_path)
        if remote_content:
            return remote_content

        local_path = target_app_path_for(getattr(gitlab_service, "target_app_path", None)) / file_path
        if local_path.exists():
            return local_path.read_text(encoding="utf-8")
        return ""

    def _write_file(self, workspace: Path, file_path: str, content: str) -> None:
        destination = workspace / file_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


class CurrencyValidationStrategy(PytestValidationStrategy):
    name = "currency_validator"


class AuthValidationStrategy(PytestValidationStrategy):
    name = "auth_validator"


class DependencyValidationStrategy(PytestValidationStrategy):
    name = "dependency_validator"


VALIDATION_STRATEGIES = {
    "generic_pytest": PytestValidationStrategy(),
    "currency_validator": CurrencyValidationStrategy(),
    "auth_validator": AuthValidationStrategy(),
    "dependency_validator": DependencyValidationStrategy(),
}


def get_validation_strategy(name: Optional[str]) -> ValidationStrategy:
    return VALIDATION_STRATEGIES.get(name or "generic_pytest", VALIDATION_STRATEGIES["generic_pytest"])
