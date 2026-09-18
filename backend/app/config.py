"""Application settings with fail-fast validation of required env vars.

Every required variable is checked at startup via ``Settings.validate_required``
so a missing Gemini key or Supabase credential aborts boot with a clear error
naming the exact variable — never a silent failure inside a request handler.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Attribute name -> environment variable name, for every variable that MUST
# be present and non-empty before the app is allowed to start.
REQUIRED_ENV_VARS: dict[str, str] = {
    "gemini_api_key_resume_parser": "GEMINI_API_KEY_RESUME_PARSER",
    "gemini_api_key_gap_mapper": "GEMINI_API_KEY_GAP_MAPPER",
    "gemini_api_key_interview_generator": "GEMINI_API_KEY_INTERVIEW_GENERATOR",
    "gemini_api_key_profile_optimizer": "GEMINI_API_KEY_PROFILE_OPTIMIZER",
    "supabase_url": "SUPABASE_URL",
    "supabase_service_role_key": "SUPABASE_SERVICE_ROLE_KEY",
}


class Settings(BaseSettings):
    """Environment-driven configuration for the HireOrHigher backend."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini — one dedicated key per module (never shared; see spec 3.1).
    gemini_api_key_resume_parser: str = ""
    gemini_api_key_gap_mapper: str = ""
    gemini_api_key_interview_generator: str = ""
    gemini_api_key_profile_optimizer: str = ""

    # Supabase (service role key is server-side only; RLS still protects
    # direct client access via the anon key on the frontend).
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Tunables with safe defaults.
    gemini_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_timeout_seconds: float = 45.0
    backend_cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 5
    upload_rate_limit_per_hour: int = 20

    # Job Radar — SerpApi (google_jobs engine). Not in REQUIRED_ENV_VARS: a
    # missing key surfaces as a 502 on that one route rather than blocking
    # boot for the rest of the app.
    serpapi_api_key: str = ""
    serpapi_timeout_seconds: float = 20.0

    @field_validator(
        "gemini_model",
        "gemini_embedding_model",
        "gemini_timeout_seconds",
        "backend_cors_origins",
        "max_upload_mb",
        "upload_rate_limit_per_hour",
        "serpapi_timeout_seconds",
        mode="before",
    )
    @classmethod
    def _empty_means_default(cls, value, info):
        """Optional vars left blank in .env (e.g. ``MAX_UPLOAD_MB=``) fall
        back to their defaults instead of failing numeric parsing."""
        if isinstance(value, str) and not value.strip():
            return cls.model_fields[info.field_name].default
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def validate_required(self) -> None:
        """Raise RuntimeError naming every missing required env variable."""
        missing = [
            env_name
            for attr, env_name in REQUIRED_ENV_VARS.items()
            if not getattr(self, attr).strip()
        ]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Copy .env.example to .env at the repo root and fill in values."
            )


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance (tests clear the cache to reload)."""
    return Settings()
