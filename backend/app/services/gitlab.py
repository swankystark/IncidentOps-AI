import datetime
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from ..config import get_target_repo, resolve_project_path, settings

class GitLabService:
    def __init__(self, project_path: Optional[str] = None, target_branch: Optional[str] = None, target_app_path: Optional[str] = None):
        self.pat = settings.GITLAB_PAT
        self.project_path = project_path or get_target_repo()
        self.target_branch = target_branch or settings.GITLAB_TARGET_BRANCH
        self.target_app_path = target_app_path if target_app_path is not None else settings.TARGET_APP_PATH
        # Encode the project path (e.g. "group/project" -> "group%2Fproject")
        self.project_encoded = self.project_path.replace("/", "%2F")
        self.base_url = f"{settings.GITLAB_BASE_URL.rstrip('/')}/api/v4"
        self.headers = {"PRIVATE-TOKEN": self.pat} if self.pat else {}

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "GitLabService":
        return cls(
            project_path=state.get("target_repo") or get_target_repo(),
            target_branch=state.get("target_branch") or settings.GITLAB_TARGET_BRANCH,
            target_app_path=state.get("target_app_path") if state.get("target_app_path") is not None else settings.TARGET_APP_PATH,
        )

    def _resolve_path(self, file_path: str) -> str:
        """Resolve repository-relative paths using the configured target app prefix."""
        prefix = (self.target_app_path or "").strip("/\\")
        normalized = file_path.replace("\\", "/")
        if prefix and not normalized.startswith(f"{prefix}/") and normalized != prefix:
            return f"{prefix}/{normalized}"
        return normalized

    def _local_file_content(self, file_path: str) -> str:
        prefix = (self.target_app_path or "").strip("/\\")
        normalized = file_path.replace("\\", "/")
        candidates = [resolve_project_path(normalized)]
        if prefix and not normalized.startswith(f"{prefix}/") and normalized != prefix:
            candidates.insert(0, resolve_project_path(f"{prefix}/{normalized}"))
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        return ""

    async def get_project_details(self) -> Dict[str, Any]:
        """Fetch project details from GitLab API or return mock in Demo mode."""
        if settings.DEMO_MODE:
            return {
                "id": 123456,
                "name": "incidentops-demo-app",
                "path_with_namespace": self.project_path,
                "web_url": f"https://gitlab.com/{self.project_path}"
            }
        
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_branch(self, branch: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a branch by name to verify branch-level repository access."""
        branch_name = branch or self.target_branch
        if settings.DEMO_MODE:
            return {"name": branch_name, "commit": {"id": "demo"}}

        async with httpx.AsyncClient() as client:
            branch_encoded = quote(branch_name, safe="")
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/branches/{branch_encoded}"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def search_commits(self, query: str, time_window: str = None) -> List[Dict[str, Any]]:
        """Search commits using query parameters or return mock in Demo mode."""
        if settings.DEMO_MODE:
            # High-fidelity mock commits related to currency regression
            if "currency" in query.lower() or "rates" in query.lower() or "report" in query.lower():
                return [
                    {
                        "id": "cf78a9c2b4e85901dc8aef02c77d0138cf18fa30",
                        "short_id": "cf78a9c2",
                        "title": "refactor: Optimize exchange rate lookup by caching live rates globally",
                        "author_name": "john_doe",
                        "author_email": "john.doe@company.com",
                        "created_at": "2026-05-25T14:22:10.000Z",
                        "message": "refactor: Optimize exchange rate lookup by caching live rates globally\n\nTo improve revenue report performance, cached current exchange rates. Caching live EUR, GBP, CAD rates locally to avoid DB query bottlenecks during dashboard loading.",
                        "parent_ids": ["e4d5c6b7"]
                    },
                    {
                        "id": "e4d5c6b7a390ef01b8cdde02377d0138cf18fa2f",
                        "short_id": "e4d5c6b7",
                        "title": "feat: Add support for monthly billing report exports",
                        "author_name": "jane_smith",
                        "created_at": "2026-05-20T09:15:00.000Z",
                        "message": "feat: Add support for monthly billing report exports"
                    }
                ]
            return []

        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/commits"
            params = {"search": query}
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
            except httpx.HTTPError:
                return []
            return []

    async def get_file_content(self, file_path: str, ref: Optional[str] = None) -> str:
        """Fetch raw file content from GitLab or return mock in Demo mode."""
        ref = ref or self.target_branch
        if settings.DEMO_MODE:
            # Return our realistic buggy currency/converter.py file
            if file_path == "currency/converter.py":
                return """# currency/converter.py
import datetime

# Live rates cache for performance
_RATES_CACHE = {"EUR": 1.18, "GBP": 1.35, "CAD": 0.75}

def convert_currency(amount: float, from_curr: str, to_curr: str, date: datetime.date = None) -> float:
    \"\"\"
    Converts an amount from one currency to another.
    Bypasses DB if rates are in the local cache.
    \"\"\"
    if from_curr == to_curr:
        return amount
        
    # Check cache for performance speedups
    if from_curr in _RATES_CACHE and to_curr == "USD":
        return amount * _RATES_CACHE[from_curr]
        
    # Fallback to database lookup for historical/uncached rates
    return amount * get_historical_rate_from_db(from_curr, to_curr, date)

def get_historical_rate_from_db(from_curr: str, to_curr: str, date: datetime.date) -> float:
    # Simulated historical exchange rates
    rates = {
        "EUR": {
            datetime.date(2026, 4, 12): 1.08,
            datetime.date(2026, 5, 27): 1.18
        }
    }
    # Default to 1.0 if not found
    if date and from_curr in rates:
        return rates[from_curr].get(date, 1.18)
    return 1.18
"""
            # Mock tests/test_currency.py
            elif file_path == "tests/test_currency.py":
                return """# tests/test_currency.py
import datetime
from currency.converter import convert_currency

def test_historical_currency_conversion():
    # Historical rate on 2026-04-12 for EUR -> USD was 1.08
    historical_date = datetime.date(2026, 4, 12)
    converted = convert_currency(100.0, "EUR", "USD", historical_date)
    # Expected: 100 * 1.08 = 108.0
    # Bug causes it to use current cached rate 1.18 -> 118.0 (Failure!)
    assert converted == 108.0, f"Expected 108.0, but got {converted}"
"""
            return f"# Simulated content for {file_path}"

        resolved_path = self._resolve_path(file_path)
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/files/{resolved_path.replace('/', '%2F')}/raw"
            params = {"ref": ref}
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.text
            except httpx.HTTPError:
                pass
            # Return empty string if file doesn't exist
            return self._local_file_content(file_path)

    async def get_pipeline_status(self, preferred_sha: Optional[str] = None) -> Dict[str, Any]:
        """Select the most relevant pipeline for the configured branch/SHA."""
        if settings.DEMO_MODE:
            return {
                "id": 887722,
                "status": "failed",
                "ref": "main",
                "sha": "cf78a9c2b4e85901dc8aef02c77d0138cf18fa30",
                "web_url": f"https://gitlab.com/{self.project_path}/-/pipelines/887722"
            }
        
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/pipelines"

            if self.target_branch:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params={"ref": self.target_branch, "per_page": 10},
                )
                if response.status_code == 200 and response.json():
                    pipelines = response.json()
                    if preferred_sha:
                        for pipeline in pipelines:
                            if pipeline.get("sha") == preferred_sha:
                                pipeline["selection_source"] = "target_branch_and_incident_sha"
                                return pipeline
                    pipelines[0]["selection_source"] = "target_branch"
                    return pipelines[0]

            if preferred_sha:
                response = await client.get(url, headers=self.headers, params={"sha": preferred_sha, "per_page": 10})
                if response.status_code == 200 and response.json():
                    pipeline = response.json()[0]
                    pipeline["selection_source"] = "incident_sha"
                    return pipeline

            response = await client.get(url, headers=self.headers, params={"status": "success", "per_page": 10})
            if response.status_code == 200 and response.json():
                pipeline = response.json()[0]
                pipeline["selection_source"] = "latest_successful"
                return pipeline

            response = await client.get(url, headers=self.headers, params={"per_page": 1})
            if response.status_code == 200 and response.json():
                pipeline = response.json()[0]
                pipeline["selection_source"] = "latest_any"
                return pipeline
            return {"status": "unknown", "selection_source": "none"}

    async def get_pipeline_test_failures(self) -> List[Dict[str, Any]]:
        """Get failing test details or return mock."""
        if settings.DEMO_MODE:
            return [
                {
                    "name": "test_historical_currency_conversion",
                    "classname": "tests.test_currency",
                    "status": "failed",
                    "failure_message": "AssertionError: Expected 108.0, but got 118.0",
                    "file": "tests/test_currency.py"
                }
            ]
        # Real GitLab test report endpoint
        # projects/:id/pipelines/:pipeline_id/test_report
        pipeline = await self.get_pipeline_status()
        p_id = pipeline.get("id")
        if not p_id or p_id == "unknown":
            return []
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/pipelines/{p_id}/test_report"
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                failures = []
                for suite in data.get("test_suites", []):
                    for case in suite.get("test_cases", []):
                        if case.get("status") == "failed":
                            failures.append(case)
                return failures
            return []

    async def create_branch(self, branch_name: str, ref: Optional[str] = None) -> bool:
        """Create a new branch in the GitLab repository. Works in both live and mock mode."""
        ref = ref or self.target_branch
        if settings.DEMO_MODE:
            print(f"[GitLab Mock] Created branch '{branch_name}' from ref '{ref}'")
            return True
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/branches"
            payload = {"branch": branch_name, "ref": ref}
            response = await client.post(url, headers=self.headers, json=payload)
            return response.status_code in [200, 201]

    async def commit_changes(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
        """Commit changes to a file on a branch. Works in both live and mock mode."""
        if settings.DEMO_MODE:
            print(f"[GitLab Mock] Committed changes to '{file_path}' on branch '{branch_name}'")
            return True

        resolved_path = self._resolve_path(file_path)
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/commits"
            payload = {
                "branch": branch_name,
                "commit_message": commit_message,
                "actions": [
                    {
                        "action": "update",
                        "file_path": resolved_path,
                        "content": content
                    }
                ]
            }
            response = await client.post(url, headers=self.headers, json=payload)
            return response.status_code in [200, 201]

    async def create_merge_request(self, source_branch: str, target_branch: str, title: str, description: str) -> Optional[str]:
        """Create a merge request and return the web URL."""
        if settings.DEMO_MODE:
            return f"https://gitlab.com/{self.project_path}/-/merge_requests/42"

        # In pure live mode
        mr_url = await self.create_merge_request_real(source_branch, target_branch, title, description)
        return mr_url

    async def create_note_on_mr(self, mr_iid: int, body: str) -> bool:
        """Add a comment (RCA report) to a merge request."""
        if settings.DEMO_MODE:
            print(f"[GitLab Mock] Posted RCA report to MR #{mr_iid}")
            return True
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/merge_requests/{mr_iid}/notes"
            response = await client.post(url, headers=self.headers, json={"body": body})
            return response.status_code in [200, 201]

    async def get_pipeline_jobs(self, pipeline_id: int) -> List[Dict[str, Any]]:
        """Get the jobs list for a specific pipeline."""
        if settings.DEMO_MODE:
            return [
                {
                    "id": 998822,
                    "name": "test:unit",
                    "status": "failed"
                }
            ]
        
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/pipelines/{pipeline_id}/jobs"
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []

    async def get_job_trace(self, job_id: int) -> str:
        """Fetch the log trace for a specific job."""
        if settings.DEMO_MODE:
            return "AssertionError: Expected 108.0, but got 118.0\npytest failures trace simulated."
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/jobs/{job_id}/trace"
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
            return ""

    # Helper functions for making real GitLab API calls directly
    async def create_branch_real(self, branch_name: str, ref: str) -> bool:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/branches"
            response = await client.post(url, headers=self.headers, json={"branch": branch_name, "ref": ref})
            return response.status_code in [200, 201]

    async def get_file_content_real(self, file_path: str, ref: str) -> str:
        resolved_path = self._resolve_path(file_path)
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/files/{resolved_path.replace('/', '%2F')}/raw"
            response = await client.get(url, headers=self.headers, params={"ref": ref})
            if response.status_code == 200:
                return response.text
            return ""

    async def commit_changes_real(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
        resolved_path = self._resolve_path(file_path)
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/repository/commits"
            payload = {
                "branch": branch_name,
                "commit_message": commit_message,
                "actions": [{"action": "update", "file_path": resolved_path, "content": content}]
            }
            response = await client.post(url, headers=self.headers, json=payload)
            return response.status_code in [200, 201]

    async def create_merge_request_real(self, source_branch: str, target_branch: str, title: str, description: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/projects/{self.project_encoded}/merge_requests"
            payload = {
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description
            }
            response = await client.post(url, headers=self.headers, json=payload)
            if response.status_code in [200, 201]:
                return response.json().get("web_url")
            if response.status_code == 409:
                existing = await client.get(
                    url,
                    headers=self.headers,
                    params={"source_branch": source_branch, "target_branch": target_branch, "state": "opened", "per_page": 1},
                )
                if existing.status_code == 200 and existing.json():
                    return existing.json()[0].get("web_url")
            return None

gitlab_service = GitLabService()
