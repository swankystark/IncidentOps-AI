import os
import subprocess
import sys
from ..database import log_to_db
from .state import AgentState
from ..config import resolve_project_path, settings
from ..incident_registry import target_app_path_for
from ..services.gitlab import GitLabService

async def run_cicd_service(state: AgentState) -> dict:
    """
    CI/CD Service: Retrieves pipeline status and failures from GitLab when available.
    If no jobs are run on GitLab (e.g. no runners), falls back to executing pytest
    locally on the actual code to retrieve real log trace outputs.
    """
    incident = state.get("incident", {})
    incident_id = incident.get("incident_db_id")
    context = state.get("retrieval", {}).get("shared_context", {})
    template = incident.get("incident_template", {})
    module = context.get("suspected_module") or template.get("module") or "currency"
    gitlab_client = GitLabService.from_state(state)

    log_to_db(incident_id, "CI/CD Service", "Retrieving latest CI/CD pipeline status from GitLab...")

    evidence = {}
    try:
        gitlab_ev = state.get("retrieval", {}).get("gitlab_evidence", {})
        commits = gitlab_ev.get("commits", [])
        commit_sha = state.get("fusion", {}).get("pinned_commit_sha") or (commits[0].get("sha") if commits else None)

        pipeline = await gitlab_client.get_pipeline_status(preferred_sha=commit_sha)
        pipeline_id = pipeline.get("id")
        pipeline_status = pipeline.get("status", "unknown")
        pipeline_ref = pipeline.get("ref", "main")
        pipeline_sha = pipeline.get("sha")
        pipeline_source = pipeline.get("selection_source", "unknown")

        from ..database import SessionLocal
        from ..models import Incident
        db = SessionLocal()
        try:
            db.query(Incident).filter(Incident.id == incident_id).update({
                "selected_pipeline_id": str(pipeline_id) if pipeline_id else None,
                "selected_pipeline_ref": pipeline_ref,
                "selected_pipeline_sha": pipeline_sha,
                "selected_pipeline_status": pipeline_status,
                "selected_pipeline_web_url": pipeline.get("web_url"),
                "selected_pipeline_source": pipeline_source,
            })
            db.commit()
        finally:
            db.close()

        jobs = []
        if pipeline_id and pipeline_status != "unknown":
            log_to_db(
                incident_id,
                "CI/CD Service",
                f"Selected GitLab pipeline #{pipeline_id} via '{pipeline_source}': status '{pipeline_status}', ref '{pipeline_ref}', sha '{pipeline_sha}'"
            )
            # Retrieve jobs of the pipeline
            jobs = await gitlab_client.get_pipeline_jobs(pipeline_id)

        # Look for failed job trace
        failed_job = None
        job_trace = ""
        if jobs:
            for j in jobs:
                if j.get("status") == "failed":
                    failed_job = j
                    break
            if failed_job:
                log_to_db(
                    incident_id,
                    "CI/CD Service",
                    f"Found failed job '{failed_job.get('name')}' (ID: {failed_job.get('id')}) on GitLab. Fetching console logs (trace)..."
                )
                job_trace = await gitlab_client.get_job_trace(failed_job.get("id"))

        if pipeline_id and pipeline_status == "failed" and failed_job and job_trace:
            # We got a real log trace from GitLab!
            log_to_db(incident_id, "CI/CD Service", "Successfully retrieved real job trace logs from GitLab.")
            
            # Simple trace parser to extract AssertionError/Traceback
            failure_message = "Unknown traceback"
            for line in job_trace.splitlines():
                if "AssertionError:" in line or "ImportError:" in line or "TypeError:" in line or "AttributeError:" in line:
                    failure_message = line.strip()
                    break
            
            evidence["pipeline"] = {
                "id": pipeline_id,
                "status": "failed",
                "ref": pipeline_ref,
                "sha": pipeline_sha or commit_sha,
                "web_url": pipeline.get("web_url"),
                "source": "gitlab_api_trace",
                "selection_source": pipeline_source
            }
            
            evidence["test_failures"] = [
                {
                    "name": failed_job.get("name"),
                    "classname": f"tests.test_{module}",
                    "status": "failed",
                    "failure_message": failure_message,
                    "file": template.get("test_target", f"tests/test_{module}.py").split("::")[0]
                }
            ]
            log_to_db(incident_id, "CI/CD Service", f"Parsed GitLab job trace failure: '{failure_message}'")

        else:
            # No job traces exist on GitLab (e.g. runner-less, configuration failure, or empty pipelines).
            # Fall back to running pytest locally on the buggy code to get the REAL pytest log.
            log_to_db(
                incident_id,
                "CI/CD Service",
                "GitLab pipeline has no job traces (no runners or pending). Running pytest locally to capture actual failure logs..."
            )
            
            # Find pytest
            pytest_path = str(resolve_project_path(os.path.join("venv", "Scripts", "pytest.exe")))
            if not os.path.exists(pytest_path):
                pytest_path = "pytest"

            # Execute pytest locally on target module tests
            app_path = incident.get("target_app_path")
            target_path = target_app_path_for(app_path)
            test_file_path = str(target_path / template.get("test_target", f"tests/test_{module}.py").split("::")[0])
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(target_path)
            
            result = subprocess.run(
                [pytest_path, test_file_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                env=env
            )
            
            test_output = result.stdout or result.stderr
            log_to_db(incident_id, "CI/CD Service", "Local pytest execution finished. Analyzing stderr/stdout logs...")
            
            # Find the failure message from output
            failure_message = ""
            test_name = f"test_{module}_failure"
            for line in test_output.splitlines():
                if "AssertionError:" in line or "ImportError:" in line or "TypeError:" in line or "AttributeError:" in line:
                    failure_message = line.strip()
                    break
                if line.startswith("FAIL: ") or line.startswith("FAILED "):
                    test_name = line.strip()
            
            if not failure_message:
                # Default parse if pattern not found
                failure_message = "Test failed in validation"
                
            evidence["pipeline"] = {
                "id": f"CI-{str(commit_sha)[:8]}",
                "status": "failed",
                "ref": "main",
                "sha": commit_sha,
                "web_url": f"https://gitlab.com/{incident.get('target_repo') or gitlab_client.project_path}/-/pipelines",
                "source": "local_pytest_run",
                "selection_source": pipeline_source
            }
            
            evidence["test_failures"] = [
                {
                    "name": test_name,
                    "classname": f"tests.test_{module}",
                    "status": "failed",
                    "failure_message": failure_message,
                    "file": template.get("test_target", f"tests/test_{module}.py").split("::")[0],
                    "full_trace": test_output
                }
            ]
            log_to_db(incident_id, "CI/CD Service", f"Captured real local pytest failure log: '{failure_message}'")

        return {
            "retrieval": {"cicd_evidence": evidence}
        }

    except Exception as e:
        log_to_db(incident_id, "CI/CD Service", f"Error collecting CI/CD status: {e}", level="ERROR")
        return {
            "retrieval": {"cicd_evidence": {"error": str(e), "test_failures": []}}
        }
