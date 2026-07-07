"""Health check: liveness plus a live Supabase connectivity probe."""

from fastapi import APIRouter

from app.db.supabase_client import get_supabase

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Report API liveness and Supabase reachability.

    Inputs: none. Uses no Gemini key (health must stay free and fast).
    Always returns 200 so load balancers see liveness; the ``supabase``
    field carries dependency status.
    """
    try:
        get_supabase().table("users").select("id").limit(1).execute()
        supabase_status = "connected"
    except Exception as exc:  # noqa: BLE001
        supabase_status = f"error: {type(exc).__name__}"
    return {"status": "ok", "supabase": supabase_status}
