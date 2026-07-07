"""Singleton Supabase client using the server-side service role key.

The service role bypasses RLS by design (the backend enforces user scoping in
the repository layer by always filtering on the authenticated user), while
RLS on every table protects direct browser access through the anon key.
"""

from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_supabase():
    """Return the cached Supabase client (imported lazily for testability)."""
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
