import json
import time
from typing import List, Optional, Type
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from ..config import settings

# ----------------------------------------------------
# Gemini Pydantic Schemas for Structured JSON Outputs
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
    file_path: str = Field(description="Relative file path of the code to patch")
    target_content: str = Field(description="The exact contiguous block of code to be replaced. Must match code in the repository exactly including indentation and whitespace.")
    replacement_content: str = Field(description="The replacement code block to swap in for target_content.")

class RCAOutput(BaseModel):
    title: str = Field(description="Title of the Root Cause Analysis report")
    summary: str = Field(description="Executive summary of the incident and impact")
    root_cause_details: str = Field(description="Detailed explanation of what caused the bug")
    remediation_details: str = Field(description="Explanation of how the patch resolves the issue and prevents future regression")
    confidence_score: float = Field(description="The final confidence score of the diagnosis (0.0 to 1.0)")


# ----------------------------------------------------
# Gemini API Service
# ----------------------------------------------------
class GeminiService:
    def __init__(self):
        # Initialize the official Google GenAI Client
        self.api_key = settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"

    def set_api_key(self, api_key: str) -> None:
        """Replace the Gemini API key for the current backend process."""
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def masked_api_key(self) -> str:
        if not self.api_key:
            return ""
        if len(self.api_key) <= 8:
            return "****"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def generate_structured(self, prompt: str, response_schema: Type[BaseModel]) -> BaseModel:
        """
        Sends a prompt to Gemini and enforces a structured JSON response matching the provided Pydantic schema class.
        """
        last_error = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.1
                    )
                )
                data = json.loads(response.text)
                return response_schema(**data)
            except Exception as e:
                last_error = e
                if "429" in str(e):
                    raise e
                if "503" in str(e) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                print(f"Error in Gemini structured generation: {e}")
                raise e
        raise last_error

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Generates standard text responses (useful for intermediate analysis or freeform summaries).
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature
            )
        )
        return response.text

gemini_service = GeminiService()
