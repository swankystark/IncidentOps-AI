from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
import re
from collections.abc import Sequence
from typing import Protocol
from .config import settings


class MetricLog(Protocol):
    agent_name: str
    message: str


def _count_files_analyzed(logs: Sequence[MetricLog]) -> int:
    paths = {
        log.message.split("'")[1]
        for log in logs
        if log.agent_name in {"GitLab Service", "Validation Service", "Patch Generation Agent"}
        and "'" in log.message
        and "file" in log.message.lower()
    }
    explicit_counts = [
        int(match.group(1))
        for log in logs
        if log.agent_name == "Repository Context"
        if (match := re.search(r"Files analyzed: (\d+)", log.message))
    ]
    return max([len(paths), *explicit_counts], default=0)

# SQLite needs check_same_thread=False for multi-threaded/async access in FastAPI
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_sqlite_schema():
    """Apply small additive SQLite migrations for existing local demo databases."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    required_incident_columns = {
        "module": "VARCHAR",
        "scenario_id": "VARCHAR",
        "validation_strategy": "VARCHAR",
        "target_repo": "VARCHAR",
        "target_branch": "VARCHAR",
        "target_app_path": "VARCHAR",
        "application_log_path": "VARCHAR",
        "selected_pipeline_id": "VARCHAR",
        "selected_pipeline_ref": "VARCHAR",
        "selected_pipeline_sha": "VARCHAR",
        "selected_pipeline_status": "VARCHAR",
        "selected_pipeline_web_url": "VARCHAR",
        "selected_pipeline_source": "VARCHAR",
        "checkpoint_state": "TEXT",
        "failure_reason": "VARCHAR",
    }
    inspector = inspect(engine)
    if "incidents" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("incidents")}
    with engine.begin() as conn:
        for name, sql_type in required_incident_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE incidents ADD COLUMN {name} {sql_type}"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_to_db(incident_id: int, agent_name: str, message: str, level: str = "INFO"):
    """Global helper to log agent activity directly to SQLite for UI timeline updates."""
    db = SessionLocal()
    try:
        from .models import AgentLog, Incident
        # Update incident status if required
        if agent_name == "Planner Agent":
            db.query(Incident).filter(Incident.id == incident_id).update({"status": "INVESTIGATING"})
        elif agent_name == "Patch Generation Agent":
            db.query(Incident).filter(Incident.id == incident_id).update({"status": "PATCHING"})
        elif agent_name == "Validation Service" and "passed" in message.lower():
            db.query(Incident).filter(Incident.id == incident_id).update({"status": "RESOLVING"})
        
        log_entry = AgentLog(
            incident_id=incident_id,
            agent_name=agent_name,
            message=message,
            level=level
        )
        db.add(log_entry)
        db.commit()
        print(f"[{agent_name}] {message}")
    except Exception as e:
        print(f"Failed to log to DB: {e}")
    finally:
        db.close()

def refresh_incident_metrics(incident_id: int):
    """Recompute persisted metrics from the current incident and agent logs."""
    db = SessionLocal()
    try:
        from .models import AgentLog, Incident, IncidentMetric

        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return

        logs = db.query(AgentLog).filter(AgentLog.incident_id == incident_id).order_by(AgentLog.id.asc()).all()
        first_ts = logs[0].timestamp if logs else incident.created_at
        last_ts = logs[-1].timestamp if logs else incident.updated_at
        elapsed = max((last_ts - first_ts).total_seconds(), 0.0) if first_ts and last_ts else 0.0

        evidence_agents = {"GitLab Service", "CI/CD Service", "Log Service"}
        sources = len({log.agent_name for log in logs if log.agent_name in evidence_agents})
        files_analyzed = _count_files_analyzed(logs)
        patch_success = bool(incident.patch_diff)
        validation_success = any(log.agent_name == "Validation Service" and "passed" in log.message.lower() for log in logs)
        mr_created = bool(incident.gitlab_mr_url)

        metric = db.query(IncidentMetric).filter(IncidentMetric.incident_id == incident_id).first()
        if not metric:
            metric = IncidentMetric(incident_id=incident_id)
            db.add(metric)
        metric.investigation_time_seconds = elapsed
        metric.evidence_sources_correlated = sources
        metric.files_analyzed = files_analyzed
        metric.root_cause_confidence = incident.confidence_score or 0
        metric.validation_success = validation_success
        metric.patch_success = patch_success
        metric.merge_request_created = mr_created
        db.commit()
    except Exception as e:
        print(f"Failed to refresh metrics: {e}")
    finally:
        db.close()
