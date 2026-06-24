"""
Backward-compatible module: exports Pydantic schemas and a provider-based service singleton.

All agent code should import schemas from here, and use `llm_service` instead of `gemini_service`.
The name `gemini_service` is kept as an alias for backward compatibility during migration.
"""
from typing import List
from pydantic import BaseModel, Field
from .llm_provider import create_provider, LLMProvider

# ----------------------------------------------------
# Pydantic Schemas for Structured JSON Outputs
# (These are provider-agnostic)
# ----------------------------------------------------
class PlannerOutput(BaseModel):
    suspected_module: str = Field(description="The suspected code module or directory, e.g. currency, auth, billing, reports")
    suspected_error_type: str = Field(description="The type of error suspected, e.g. logic regression, null pointer, dependency mismatch")
    time_window: str = Field(description="The time range of interest, e.g. last 7 days, last 24 hours")
    priority_signals: List[str] = Field(description="List of priority signals (keywords, files, commit messages) for retrieval agents")

class EvidenceFusionOutput(BaseModel):
    root_cause: str = Field(description="A concise summary of the discovered root cause of the incident")
    confidence: float = Field(description="Confidence score of the root cause diagnosis between 0.0 and 1.0 (e.g. 0.92)")
    affected_file: str = Field(description="The path to the source file that contains the bug, relative to repo root")
    evidence_chain: List[str] = Field(description="A list of statements connecting logs, pipeline failures, and commits chronologically")
    refinement_needed: bool = Field(description="True if we need to query GitLab Agent for a second-pass targeted refinement")
    refinement_query: str = Field(description="Specific target query or file path to run in the second-pass search if refinement_needed is True, otherwise empty string")

class PatchOutput(BaseModel):
    explanation: str = Field(description="Brief explanation of the proposed patch and why it resolves the root cause")
    replacement_content: str = Field(description="The replacement code block to swap in for the provided target code. Must be valid syntactically and completely replace the given block.")

class RCAOutput(BaseModel):
    title: str = Field(description="Title of the Root Cause Analysis report")
    summary: str = Field(description="Executive summary of the incident and impact")
    root_cause_details: str = Field(description="Detailed explanation of what caused the bug")
    remediation_details: str = Field(description="Explanation of how the patch resolves the issue and prevents future regression")
    confidence_score: float = Field(description="The final confidence score of the diagnosis (0.0 to 1.0)")


# ----------------------------------------------------
# Provider-based singleton
# ----------------------------------------------------
llm_service: LLMProvider = create_provider()

# Backward-compatible alias
gemini_service = llm_service
