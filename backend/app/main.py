"""FastAPI application factory for the HireOrHigher backend.

Run locally with:  uvicorn app.main:app --reload  (from the backend/ dir).
OpenAPI docs are intentionally enabled at /docs (spec 11).
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    analytics,
    gap_reports,
    health,
    interviews,
    profiles,
    resumes,
)
from app.config import get_settings
from app.core.gemini import GeminiError


async def _gemini_error_handler(request: Request, exc: GeminiError) -> JSONResponse:
    """Surface Gemini failures (after their one retry) as a clear 502."""
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def create_app() -> FastAPI:
    """Build the app, failing fast if any required env variable is missing."""
    settings = get_settings()
    settings.validate_required()

    app = FastAPI(
        title="HireOrHigher API",
        description=(
            "AI-powered career-readiness platform: resume parsing + scoring, "
            "gap-to-job mapping, mock interviews, and profile optimization — "
            "all driven by a single parsed resume."
        ),
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(GeminiError, _gemini_error_handler)

    app.include_router(health.router, prefix="/api")
    app.include_router(resumes.router, prefix="/api")
    app.include_router(gap_reports.router, prefix="/api")
    app.include_router(interviews.router, prefix="/api")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    return app


app = create_app()
