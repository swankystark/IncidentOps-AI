from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import RepositoryValidationRequest, RepositoryValidationResponse
from ..services.gitlab import GitLabService
from ..services.gemini import llm_service

router = APIRouter(prefix="/config", tags=["config"])


class LLMKeyUpdate(BaseModel):
    api_key: str


@router.get("/llm")
def get_llm_config():
    return {
        "provider": llm_service.provider_name,
        "configured": llm_service.has_api_key(),
        "masked_api_key": llm_service.masked_api_key(),
    }


# Backward-compatible alias
@router.get("/gemini")
def get_gemini_config():
    return get_llm_config()


@router.post("/llm")
def update_llm_key(payload: LLMKeyUpdate):
    api_key = payload.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    llm_service.set_api_key(api_key)
    return {
        "provider": llm_service.provider_name,
        "configured": True,
        "masked_api_key": llm_service.masked_api_key(),
    }


# Backward-compatible alias
@router.post("/gemini")
def update_gemini_key(payload: LLMKeyUpdate):
    return update_llm_key(payload)


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
