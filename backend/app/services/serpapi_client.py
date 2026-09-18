"""SerpApi client wrapper: google_jobs engine, timeout, retry-once.

Mirrors the retry/timeout discipline in ``app.core.gemini`` — one hard
timeout per request and exactly one retry before a ``SerpApiError`` surfaces
to the route layer, which maps it to a 502 the same way ``GeminiError`` does.
Job Radar spends exactly one SerpApi search per ``POST /api/job-radar`` call,
regardless of how many listings come back.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


class SerpApiError(Exception):
    """Raised when a SerpApi call fails after its one retry (surfaced as 502)."""

    def __init__(self, detail: str):
        super().__init__(
            f"The job search service is temporarily unavailable ({detail}). "
            "Please try again in a moment."
        )


def _normalize_listing(raw: dict) -> dict | None:
    """One ``jobs_results`` entry -> our flat shape, or ``None`` to drop it.

    A listing with no description text can't be gap-mapped, so it's dropped
    here rather than surfacing as a scorable-but-empty result.
    """
    description = raw.get("description")
    if not description:
        return None

    apply_options = raw.get("apply_options") or []
    job_url = (
        raw.get("share_link")
        or (apply_options[0].get("link") if apply_options else None)
        or ""
    )
    return {
        "title": raw.get("title") or "",
        "company_name": raw.get("company_name") or "",
        "location": raw.get("location") or "",
        "description": description,
        "job_url": job_url,
    }


def _normalize_results(payload: dict) -> list[dict]:
    """``jobs_results`` -> deduplicated, description-having listings.

    A zero-result search (missing/empty ``jobs_results``) is a valid outcome,
    not an error, so it simply yields an empty list.
    """
    raw_results = payload.get("jobs_results") or []
    seen_urls: set[str] = set()
    listings: list[dict] = []
    for raw in raw_results:
        listing = _normalize_listing(raw)
        if listing is None:
            continue
        url = listing["job_url"]
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        listings.append(listing)
    return listings


class SerpApiClient:
    """Thin wrapper over SerpApi's ``google_jobs`` engine.

    Inputs: none at construction — reads ``SERPAPI_API_KEY`` from settings.
    """

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.serpapi_api_key
        self.timeout_seconds = settings.serpapi_timeout_seconds

    def search_jobs(self, role: str, location: str) -> list[dict]:
        """Run one ``google_jobs`` search and return normalized listings.

        Inputs: ``role`` (goes to the ``q`` param alone) and ``location`` (its
        own ``location`` param — SerpApi's ``google_jobs`` engine supports it
        natively, so it's never concatenated into ``q``). Retries exactly
        once on any failure, then raises ``SerpApiError``.
        """
        params = {
            "engine": "google_jobs",
            "q": role,
            "location": location,
            "api_key": self._api_key,
        }
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                response = httpx.get(
                    SERPAPI_URL, params=params, timeout=self.timeout_seconds
                )
                response.raise_for_status()
                return _normalize_results(response.json())
            except Exception as exc:  # noqa: BLE001 — any failure triggers the single retry
                last_error = exc
                logger.warning("SerpApi call failed attempt=%d: %s", attempt, exc)
        raise SerpApiError(str(last_error))
