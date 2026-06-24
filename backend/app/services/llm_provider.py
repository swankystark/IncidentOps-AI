"""
LLM Provider Abstraction for IncidentOps AI.

Supports GeminiProvider and GroqProvider.
Selection via MODEL_PROVIDER env var (default: groq).
"""
import json
import time
from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel


class LLMProvider(ABC):
    """Minimal LLM provider interface."""

    @abstractmethod
    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """Generate freeform text from a prompt."""
        ...

    @abstractmethod
    def generate_structured(self, prompt: str, response_schema: Type[BaseModel]) -> BaseModel:
        """Generate a structured JSON response matching a Pydantic schema."""
        ...

    @abstractmethod
    def has_api_key(self) -> bool:
        ...

    @abstractmethod
    def set_api_key(self, api_key: str) -> None:
        ...

    def masked_api_key(self) -> str:
        key = getattr(self, "api_key", "") or ""
        if not key:
            return ""
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class GeminiProvider(LLMProvider):
    """Google Gemini provider using the official google-genai SDK."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._init_client()

    def _init_client(self):
        if self.api_key:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        else:
            self._client = None
        self.model = "gemini-2.5-flash"

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self._init_client()

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        from google.genai import types
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return response.text

    def generate_structured(self, prompt: str, response_schema: Type[BaseModel]) -> BaseModel:
        from google.genai import types
        last_error = None
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.1,
                    ),
                )
                data = json.loads(response.text)
                return response_schema(**data)
            except Exception as e:
                last_error = e
                if "429" in str(e):
                    raise
                if "503" in str(e) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise last_error


class GroqProvider(LLMProvider):
    """Groq provider using the groq Python SDK."""

    # Preferred models in priority order
    MODELS = [
        "llama-3.1-8b-instant",
    ]

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._init_client()

    def _init_client(self):
        if self.api_key:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        else:
            self._client = None
        self.model = self.MODELS[0]

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self._init_client()

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "groq"

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        last_error = None
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "429" in err_str or "rate_limit" in err_str:
                    raise
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise last_error

    def generate_structured(self, prompt: str, response_schema: Type[BaseModel]) -> BaseModel:
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond with ONLY valid JSON matching this exact schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do NOT include any text outside the JSON object. "
            f"Do NOT wrap the JSON in markdown code fences. "
            f"Respond with raw JSON only."
        )
        last_error = None
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": structured_prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw_text = response.choices[0].message.content
                # Strip markdown fences if the model wraps anyway
                cleaned = raw_text.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    cleaned = "\n".join(lines)
                data = json.loads(cleaned)
                return response_schema(**data)
            except json.JSONDecodeError as e:
                last_error = e
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "429" in err_str or "rate_limit" in err_str:
                    raise
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise last_error


def create_provider(provider_name: str = "", api_key: str = "") -> LLMProvider:
    """Simple factory. No registry, no plugins, no dynamic loading."""
    import os
    name = (provider_name or os.environ.get("MODEL_PROVIDER", "groq")).lower().strip()
    if name == "gemini":
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        return GeminiProvider(api_key=key)
    elif name == "groq":
        key = api_key or os.environ.get("GROQ_API_KEY", "")
        return GroqProvider(api_key=key)
    else:
        raise ValueError(f"Unknown provider: {name}. Supported: gemini, groq")
