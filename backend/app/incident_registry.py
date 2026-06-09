import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import resolve_project_path, settings


@lru_cache(maxsize=1)
def load_incident_templates() -> List[Dict[str, Any]]:
    registry_path = resolve_project_path(settings.INCIDENT_REGISTRY_PATH)
    if not registry_path.exists():
        return []
    with registry_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Incident registry must be a JSON array.")
    return data


def save_incident_templates(templates: List[Dict[str, Any]]) -> None:
    registry_path = resolve_project_path(settings.INCIDENT_REGISTRY_PATH)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2)
        f.write("\n")
    load_incident_templates.cache_clear()


def get_incident_template(ticket_id: str) -> Optional[Dict[str, Any]]:
    normalized = ticket_id.upper()
    for template in load_incident_templates():
        if str(template.get("id", "")).upper() == normalized:
            return template
    return None


def upsert_incident_template(template: Dict[str, Any]) -> Dict[str, Any]:
    if not template.get("id"):
        raise ValueError("Incident template requires an id.")
    templates = load_incident_templates()
    normalized = str(template["id"]).upper()
    replaced = False
    updated = []
    for existing in templates:
        if str(existing.get("id", "")).upper() == normalized:
            updated.append(template)
            replaced = True
        else:
            updated.append(existing)
    if not replaced:
        updated.append(template)
    save_incident_templates(updated)
    return template


def delete_incident_template(ticket_id: str) -> bool:
    normalized = ticket_id.upper()
    templates = load_incident_templates()
    updated = [t for t in templates if str(t.get("id", "")).upper() != normalized]
    if len(updated) == len(templates):
        return False
    save_incident_templates(updated)
    return True


def target_app_path() -> Path:
    return resolve_project_path(settings.TARGET_APP_PATH)


def application_log_path() -> Path:
    return resolve_project_path(settings.APPLICATION_LOG_PATH)


def target_app_path_for(path_value: str | None) -> Path:
    return resolve_project_path(path_value if path_value is not None else settings.TARGET_APP_PATH)


def application_log_path_for(path_value: str | None) -> Path:
    return resolve_project_path(path_value if path_value is not None else settings.APPLICATION_LOG_PATH)
