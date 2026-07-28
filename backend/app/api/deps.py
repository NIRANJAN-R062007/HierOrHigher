"""Shared FastAPI dependencies: auth, repository, per-module Gemini clients,
and the upload rate limits.

Tests override these with ``app.dependency_overrides`` to inject fakes, which
is what keeps the module integration tests hermetic (no network, no keys).
"""

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import get_settings
from app.core.gemini import GeminiClient
from app.core.rate_limit import SlidingWindowRateLimiter
from app.db.repository import SupabaseRepository
from app.db.supabase_client import get_supabase

_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    id: str
    email: str | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """Resolve the Supabase Auth access token from the Authorization header.

    Inputs: ``Authorization: Bearer <supabase access token>``.
    Uses no Gemini key. Raises 401 for missing/invalid tokens.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token. Sign in and retry.",
        )
    try:
        result = get_supabase().auth.get_user(credentials.credentials)
        user = result.user
        if user is None:
            raise ValueError("token did not resolve to a user")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Sign in again.",
        ) from exc
    return AuthenticatedUser(id=str(user.id), email=user.email)


def get_repository() -> SupabaseRepository:
    return SupabaseRepository(get_supabase())


# One factory per module so each endpoint is visibly bound to its own key.


def get_resume_parser_gemini() -> GeminiClient:
    """Gemini client using GEMINI_API_KEY_RESUME_PARSER (module 5.1)."""
    return GeminiClient("resume_parser")


def get_gap_mapper_gemini() -> GeminiClient:
    """Gemini client using GEMINI_API_KEY_GAP_MAPPER (module 5.2)."""
    return GeminiClient("gap_mapper")


def get_interview_generator_gemini() -> GeminiClient:
    """Gemini client using GEMINI_API_KEY_INTERVIEW_GENERATOR (module 5.3)."""
    return GeminiClient("interview_generator")


def get_profile_optimizer_gemini() -> GeminiClient:
    """Gemini client using GEMINI_API_KEY_PROFILE_OPTIMIZER (module 5.4)."""
    return GeminiClient("profile_optimizer")


@lru_cache
def _upload_limiter() -> SlidingWindowRateLimiter:
    settings = get_settings()
    return SlidingWindowRateLimiter(
        max_events=settings.upload_rate_limit_per_hour, window_seconds=3600
    )


def enforce_upload_rate_limit(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Throttle upload-shaped endpoints per user to protect Gemini quota."""
    if not _upload_limiter().allow(user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many uploads in the last hour. Please wait and retry.",
        )
    return user


@lru_cache
def _apply_limiter() -> SlidingWindowRateLimiter:
    settings = get_settings()
    return SlidingWindowRateLimiter(
        max_events=settings.apply_rate_limit_per_hour, window_seconds=3600
    )


def _client_ip(request: Request) -> str:
    """Best-effort caller IP for throttling.

    Behind a proxy (the deployed backend runs behind one) every request
    arrives from the proxy's address, which would collapse all applicants into
    a single bucket and lock out the endpoint for everyone, so the forwarded
    client is preferred when present. That header is spoofable, which is
    acceptable here precisely because this limiter guards Gemini spend rather
    than access to anything — and the posting id in the key still bounds the
    damage to one posting.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_apply_rate_limit(posting_id: str, request: Request) -> None:
    """Throttle the public apply endpoint, which has no user to key on.

    Same ``SlidingWindowRateLimiter`` the signed-in uploads use — it takes an
    arbitrary string key — keyed by posting + client IP instead of a user id,
    so one noisy applicant can't exhaust a posting's Gemini budget and can't
    affect any other posting either.
    """
    if not _apply_limiter().allow(f"{posting_id}:{_client_ip(request)}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many applications submitted from here. "
            "Please wait a little and try again.",
        )
