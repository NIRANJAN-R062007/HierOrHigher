"""POST /ml/score — offline resume-to-job match scoring (no Gemini).

Serves the trained match-scorer bundle from the repo-root ``ml`` package so
the Gap-to-Job Mapper gets fast, free, deterministic scores. Gemini is only
recommended (``recommend_gemini_review``) when the model is unsure: low
confidence or a score in the ambiguous 45-55 band.

The model is loaded ONCE at startup (lifespan hook in main.py); if the
artifact is missing or corrupt the endpoint degrades to 503 instead of
taking the whole backend down.
"""

import hashlib
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_MAX_CHARS = 50_000

_scorer = None
_load_error: str | None = None


def load_scorer() -> None:
    """Load the joblib bundle once at startup; never crash the backend."""
    global _scorer, _load_error
    try:
        if str(_REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(_REPO_ROOT))
        from ml.inference import MatchScorer

        _scorer = MatchScorer()
        logger.info("ML match scorer loaded (winner: %s)", _scorer.winner)
    except Exception as exc:  # noqa: BLE001 — degrade to 503, don't crash
        _load_error = f"{type(exc).__name__}: {exc}"
        logger.warning("ML match scorer unavailable: %s", _load_error)


class ScoreRequest(BaseModel):
    """Raw texts to score; oversized or blank input is a 422."""

    resume_text: str = Field(min_length=1, max_length=_MAX_CHARS)
    job_description: str = Field(min_length=1, max_length=_MAX_CHARS)

    @field_validator("resume_text", "job_description")
    @classmethod
    def _not_just_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty or whitespace-only")
        return value


def _cache_key(req: ScoreRequest) -> str:
    return hashlib.sha256(
        (req.resume_text + req.job_description).encode("utf-8")
    ).hexdigest()


def _cache_get(content_hash: str) -> dict | None:
    try:
        rows = (
            get_supabase()
            .table("ml_score_cache")
            .select("response")
            .eq("content_hash", content_hash)
            .limit(1)
            .execute()
            .data
        )
        return rows[0]["response"] if rows else None
    except Exception as exc:  # noqa: BLE001 — cache is best-effort
        logger.warning("ml_score_cache read failed: %s", exc)
        return None


def _cache_put(content_hash: str, response: dict) -> None:
    try:
        get_supabase().table("ml_score_cache").upsert(
            {"content_hash": content_hash, "response": response}
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ml_score_cache write failed: %s", exc)


@router.post("/score")
def score_match(req: ScoreRequest) -> dict:
    """Score a resume against a job description with the offline model.

    Inputs: raw resume + JD text (each 1..50k chars). Uses no Gemini key.
    Checks the Supabase content-hash cache before predicting (spec 3.3
    strategy, same as every Gemini module). Response is the ML output
    contract plus ``recommend_gemini_review`` for the hybrid fallback.
    """
    if _scorer is None:
        raise HTTPException(
            status_code=503,
            detail="ML scoring model is not available"
            + (f" ({_load_error})" if _load_error else "")
            + ". Train it with: python -m ml.train",
        )

    content_hash = _cache_key(req)
    cached = _cache_get(content_hash)
    if cached is not None:
        return cached

    result = _scorer.predict(req.resume_text, req.job_description)
    result["recommend_gemini_review"] = bool(
        result["confidence"] < 0.6 or 45.0 <= result["match_score"] <= 55.0
    )
    _cache_put(content_hash, result)
    return result
