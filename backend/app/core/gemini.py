"""Gemini client wrapper: one dedicated API key per module, timeout, retry-once.

Each module builds its own ``GeminiClient`` bound to its own env-configured
key (spec 3.1), so quota and cost stay isolated per module. Every call runs
with a hard timeout and exactly one retry before a ``GeminiError`` surfaces
to the route layer (spec 9). All generation uses Gemini structured output
(JSON mode with a Pydantic response schema) — free-text parsing with regex is
deliberately impossible through this wrapper (spec 3.2).
"""

import logging
from typing import TypeVar

from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

# Module name -> (Settings attribute holding its key, env variable name).
MODULE_KEYS: dict[str, tuple[str, str]] = {
    "resume_parser": ("gemini_api_key_resume_parser", "GEMINI_API_KEY_RESUME_PARSER"),
    "gap_mapper": ("gemini_api_key_gap_mapper", "GEMINI_API_KEY_GAP_MAPPER"),
    "interview_generator": (
        "gemini_api_key_interview_generator",
        "GEMINI_API_KEY_INTERVIEW_GENERATOR",
    ),
    "profile_optimizer": (
        "gemini_api_key_profile_optimizer",
        "GEMINI_API_KEY_PROFILE_OPTIMIZER",
    ),
}


class GeminiError(Exception):
    """Raised when a Gemini call fails after its one retry (surfaced as 502)."""

    def __init__(self, module: str, detail: str):
        self.module = module
        super().__init__(
            f"The AI service for '{module}' is temporarily unavailable ({detail}). "
            "Please try again in a moment."
        )


class GeminiClient:
    """Thin wrapper over google-genai bound to a single module's API key.

    Inputs: module name (must be a key of ``MODULE_KEYS``).
    Uses: the Gemini key named by ``MODULE_KEYS[module][1]``.
    """

    def __init__(self, module: str):
        settings = get_settings()
        attr, env_name = MODULE_KEYS[module]
        self.module = module
        self.env_var = env_name
        self._api_key = getattr(settings, attr)
        self.model = settings.gemini_model
        self.embedding_model = settings.gemini_embedding_model
        self.timeout_seconds = settings.gemini_timeout_seconds
        self._sdk_client = None

    def _client(self):
        """Lazily construct the google-genai client (imported here so tests
        that inject fakes never require the SDK or a network connection)."""
        if self._sdk_client is None:
            from google import genai

            self._sdk_client = genai.Client(
                api_key=self._api_key,
                http_options={"timeout": int(self.timeout_seconds * 1000)},
            )
        return self._sdk_client

    def generate_structured(
        self,
        prompt: str,
        schema: type[TModel],
        *,
        max_output_tokens: int,
        temperature: float = 0.2,
    ) -> TModel:
        """Run one structured-output generation and return a validated model.

        Inputs: full prompt text (untrusted content already delimited by the
        caller via ``wrap_untrusted``), a Pydantic schema for JSON mode, and a
        per-task token ceiling so a single call can't run away in cost.
        Retries exactly once on any failure, then raises ``GeminiError``.
        """
        config: dict = {
            "response_mime_type": "application/json",
            "response_schema": schema,
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
        }
        # Every caller of this method wants one deterministic JSON object, not
        # reasoning, so thinking is always off. This is not just a cost knob:
        # thinking tokens are drawn from ``max_output_tokens``, so a thinking
        # model can spend the whole ceiling deliberating and return truncated
        # JSON that fails schema validation. This was version-gated on "2.5"
        # until the default model moved to gemini-3.5-flash, at which point the
        # gate silently stopped matching — JD extraction then burned 979 of its
        # 1024 tokens thinking, left 30 for an answer needing 293, and 502'd.
        # Applies to any model that accepts a zero budget; "pro" tiers enforce a
        # non-zero floor and would reject this outright rather than fail quietly.
        config["thinking_config"] = {"thinking_budget": 0}

        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                response = self._client().models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                parsed = response.parsed
                if isinstance(parsed, schema):
                    return parsed
                # Fall back to validating raw text if the SDK didn't parse.
                return schema.model_validate_json(response.text)
            except Exception as exc:  # noqa: BLE001 — any failure triggers the single retry
                last_error = exc
                logger.warning(
                    "Gemini call failed for module=%s attempt=%d: %s",
                    self.module,
                    attempt,
                    exc,
                )
        raise GeminiError(self.module, str(last_error))

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input.

        Uses the same module key as generation (the gap mapper is the only
        module that calls this). Retries once, then raises ``GeminiError``.
        """
        if not texts:
            return []
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                result = self._client().models.embed_content(
                    model=self.embedding_model, contents=texts
                )
                return [list(e.values) for e in result.embeddings]
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Gemini embed failed for module=%s attempt=%d: %s",
                    self.module,
                    attempt,
                    exc,
                )
        raise GeminiError(self.module, str(last_error))
