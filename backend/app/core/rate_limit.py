"""In-memory sliding-window rate limiter for per-user upload throttling.

Protects the per-module Gemini quotas from repeated or scripted submissions
(spec 4 and 9). In-memory is intentional for the MVP's single backend
process; swap for a Redis-backed window if the API is ever scaled out.
"""

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Allow at most ``max_events`` per ``window_seconds`` per key."""

    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record an attempt for ``key``; return False if over the limit."""
        now = time.monotonic()
        with self._lock:
            window = self._events[key]
            cutoff = now - self.window_seconds
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= self.max_events:
                return False
            window.append(now)
            return True
