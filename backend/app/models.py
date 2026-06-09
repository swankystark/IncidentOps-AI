from datetime import datetime
from sqlalchemy import Column, Boolean, Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional, List
from .database import Base

# SQLAlchemy Database Models
class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True, nullable=False)
    scenario_id = Column(String, index=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    module = Column(String, nullable=True)
    validation_strategy = Column(String, nullable=True)
    target_repo = Column(String, nullable=True)
    target_branch = Column(String, nullable=True)
    target_app_path = Column(String, nullable=True)
    application_log_path = Column(String, nullable=True)
    selected_pipeline_id = Column(String, nullable=True)
    selected_pipeline_ref = Column(String, nullable=True)
    selected_pipeline_sha = Column(String, nullable=True)
    selected_pipeline_status = Column(String, nullable=True)
    selected_pipeline_web_url = Column(String, nullable=True)
    selected_pipeline_source = Column(String, nullable=True)
    status = Column(String, default="INVESTIGATING", nullable=False)  # INVESTIGATING, PATCHING, RESOLVED, FAILED
    gitlab_mr_url = Column(String, nullable=True)
    rca_report = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    patch_diff = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    logs = relationship("AgentLog", back_populates="incident", cascade="all, delete-orphan")
    metrics = relationship("IncidentMetric", back_populates="incident", uselist=False, cascade="all, delete-orphan")

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String, default="INFO", nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    incident = relationship("Incident", back_populates="logs")

class IncidentMetric(Base):
    __tablename__ = "incident_metrics"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), unique=True, nullable=False)
    investigation_time_seconds = Column(Float, default=0.0, nullable=False)
    evidence_sources_correlated = Column(Integer, default=0, nullable=False)
    files_analyzed = Column(Integer, default=0, nullable=False)
    root_cause_confidence = Column(Integer, default=0, nullable=False)
    validation_success = Column(Boolean, default=False, nullable=False)
    patch_success = Column(Boolean, default=False, nullable=False)
    merge_request_created = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    incident = relationship("Incident", back_populates="metrics")


# Pydantic Validation Schemas
class AgentLogBase(BaseModel):
    agent_name: str
    message: str
    level: str = "INFO"
    timestamp: datetime

    class Config:
        from_attributes = True

class AgentLogCreate(BaseModel):
    agent_name: str
    message: str
    level: str = "INFO"

class AgentLogResponse(AgentLogBase):
    id: int
    incident_id: int

class IncidentBase(BaseModel):
    ticket_id: str
    title: str
    description: str
    scenario_id: Optional[str] = None
    target_repo: Optional[str] = None
    target_branch: Optional[str] = None
    target_app_path: Optional[str] = None
    application_log_path: Optional[str] = None

class IncidentCreate(IncidentBase):
    pass

class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    gitlab_mr_url: Optional[str] = None
    rca_report: Optional[str] = None
    confidence_score: Optional[int] = None
    patch_diff: Optional[str] = None

class IncidentResponse(IncidentBase):
    id: int
    module: Optional[str] = None
    validation_strategy: Optional[str] = None
    selected_pipeline_id: Optional[str] = None
    selected_pipeline_ref: Optional[str] = None
    selected_pipeline_sha: Optional[str] = None
    selected_pipeline_status: Optional[str] = None
    selected_pipeline_web_url: Optional[str] = None
    selected_pipeline_source: Optional[str] = None
    status: str
    gitlab_mr_url: Optional[str] = None
    rca_report: Optional[str] = None
    confidence_score: Optional[int] = None
    patch_diff: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class IncidentDetailResponse(IncidentResponse):
    logs: List[AgentLogResponse] = []

class IncidentMetricResponse(BaseModel):
    investigation_time_seconds: float = 0
    evidence_sources_correlated: int = 0
    files_analyzed: int = 0
    root_cause_confidence: int = 0
    validation_success: bool = False
    patch_success: bool = False
    merge_request_created: bool = False

    class Config:
        from_attributes = True

class PlatformMetricsResponse(BaseModel):
    total_incidents: int
    average_investigation_time_seconds: float
    evidence_sources_correlated: int
    files_analyzed: int
    average_root_cause_confidence: float
    validation_success_rate: float
    patch_success_rate: float
    merge_requests_created: int

class RepositoryValidationRequest(BaseModel):
    target_repo: str
    target_branch: str = "main"

class RepositoryValidationResponse(BaseModel):
    ok: bool
    target_repo: str
    target_branch: str
    project_name: Optional[str] = None
    web_url: Optional[str] = None
    message: str

class IncidentTemplate(BaseModel):
    id: str
    title: str
    description: str
    module: str
    validation: str
    error_type: Optional[str] = None
    priority_signals: List[str] = []
    expected_root_cause: Optional[str] = None
    target_file: Optional[str] = None
    test_target: Optional[str] = None
    supporting_files: List[str] = []
    trigger: Optional[dict] = None
