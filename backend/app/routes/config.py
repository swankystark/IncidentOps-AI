from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import RepositoryValidationRequest, RepositoryValidationResponse
from ..services.gitlab import GitLabService
from ..services.gemini import gemini_service

router = APIRouter(prefix="/config", tags=["config"])


class GeminiKeyUpdate(BaseModel):
    api_key: str


@router.get("/gemini")
def get_gemini_config():
    return {
        "configured": gemini_service.has_api_key(),
        "masked_api_key": gemini_service.masked_api_key(),
    }


@router.post("/gemini")
def update_gemini_key(payload: GeminiKeyUpdate):
    api_key = payload.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is required")
    gemini_service.set_api_key(api_key)
    return {
        "configured": True,
        "masked_api_key": gemini_service.masked_api_key(),
    }


@router.post("/repository/validate", response_model=RepositoryValidationResponse)
async def validate_repository(payload: RepositoryValidationRequest):
    target_repo = payload.target_repo.strip()
    target_branch = payload.target_branch.strip() or "main"
    if not target_repo:
        raise HTTPException(status_code=400, detail="GitLab target repository is required")

    gitlab = GitLabService(project_path=target_repo, target_branch=target_branch, target_app_path="")
    try:
        project = await gitlab.get_project_details()
    except Exception as exc:
        return RepositoryValidationResponse(
            ok=False,
            target_repo=target_repo,
            target_branch=target_branch,
            message=f"GitLab project lookup failed: {exc}",
        )

    try:
        await gitlab.get_branch(target_branch)
    except Exception as exc:
        return RepositoryValidationResponse(
            ok=False,
            target_repo=target_repo,
            target_branch=target_branch,
            project_name=project.get("path_with_namespace") or project.get("name"),
            web_url=project.get("web_url"),
            message=f"Repository exists, but branch '{target_branch}' could not be accessed: {exc}",
        )

    return RepositoryValidationResponse(
        ok=True,
        target_repo=target_repo,
        target_branch=target_branch,
        project_name=project.get("path_with_namespace") or project.get("name"),
        web_url=project.get("web_url"),
        message=f"Repository '{target_repo}' is accessible on branch '{target_branch}'.",
    )
