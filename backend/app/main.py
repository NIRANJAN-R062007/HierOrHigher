"""FastAPI application factory for the HireOrHigher backend.

Run locally with:  uvicorn app.main:app --reload  (from the backend/ dir).
OpenAPI docs are intentionally enabled at /docs (spec 11).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.config import get_settings


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

    app.include_router(health.router, prefix="/api")
    return app


app = create_app()
