import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(..., validation_alias="GEMINI_API_KEY")
    GITLAB_PAT: str = Field(..., validation_alias="GITLAB_PAT")
    GITLAB_TARGET_REPO: str = Field("", validation_alias="GITLAB_TARGET_REPO")
    GITLAB_PROJECT: str = Field("", validation_alias="GITLAB_PROJECT")
    GITLAB_TARGET_BRANCH: str = Field("main", validation_alias="GITLAB_TARGET_BRANCH")
    GITLAB_BASE_URL: str = Field("https://gitlab.com", validation_alias="GITLAB_BASE_URL")
    DATABASE_URL: str = Field("sqlite:///./incidentops.db", validation_alias="DATABASE_URL")
    TARGET_APP_PATH: str = Field("", validation_alias="TARGET_APP_PATH")
    APPLICATION_LOG_PATH: str = Field("application.log", validation_alias="APPLICATION_LOG_PATH")
    INCIDENT_REGISTRY_PATH: str = Field("incidents.json", validation_alias="INCIDENT_REGISTRY_PATH")
    DEFAULT_INCIDENT_ID: str = Field("INC-101", validation_alias="DEFAULT_INCIDENT_ID")
    ENABLE_MODEL_FALLBACKS: bool = Field(False, validation_alias="ENABLE_MODEL_FALLBACKS")
    
    # Enable simulation mode for local pytest execution and logs
    DEMO_MODE: bool = Field(True, validation_alias="DEMO_MODE")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def get_target_repo() -> str:
    """Return the configured GitLab target repository, preserving old env compatibility."""
    return settings.GITLAB_TARGET_REPO or settings.GITLAB_PROJECT

def resolve_project_path(path_value: str) -> Path:
    """Resolve repo-relative paths consistently from the platform project root."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
