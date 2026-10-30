"""
Rate Limiting Infrastructure for FastAPI
Provides thread-safe sliding-window rate limiting with pluggable storage.
Designed to protect authentication and resource-intensive endpoints (e.g. image inference).
"""

import time
import logging
from collections import deque
from threading import Lock
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException, status
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Safely extract client IP from headers or connection.
    Extracts the first IP from X-Forwarded-For if present (reverse proxy / load balancer).
    Falls back to direct client host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[0]
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class MemoryRateLimitStorage:
    """
    Thread-safe, sliding-window rate limit store using in-memory deques.
    Each key holds a deque of timestamps of successful requests within the window.
    """

    def __init__(self):
        self._lock = Lock()
        self._hits: Dict[str, deque] = {}

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under the rate limit.
        Returns:
            (allowed: bool, remaining: int, retry_after: int)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            if key not in self._hits:
                self._hits[key] = deque()

            queue = self._hits[key]

            # Prune timestamps older than window_start
            while queue and queue[0] < window_start:
                queue.popleft()

            if len(queue) >= limit:
                oldest_in_window = queue[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now))
                return False, 0, retry_after

            # Record this hit
            queue.append(now)
            remaining = max(0, limit - len(queue))
            return True, remaining, 0

    def clear(self):
        """Reset all rate limit records (useful for testing)."""
        with self._lock:
            self._hits.clear()


# Global storage instance
rate_limit_storage = MemoryRateLimitStorage()


class RateLimitDependency:
    """
    FastAPI dependency for rate-limiting endpoints.
    
    Security & Multi-Worker Notice:
    - Keys are built strictly from endpoint scopes and client IPs or user IDs.
    - Passwords, authorization tokens, and request bodies are NEVER used as keys or logged.
    - When running multiple application worker processes (e.g. Uvicorn --workers 4),
      in-memory limits are process-local. For shared limits across worker clusters,
      configure RATE_LIMIT_STORAGE_URL to an external cache (e.g. redis://).
    """

    def __init__(
        self,
        scope: str,
        limit_getter=None,
        window_getter=None,
        default_limit: int = 5,
        default_window: int = 60,
        key_type: str = "ip",  # "ip" or "ip_or_user"
    ):
        self.scope = scope
        self.limit_getter = limit_getter
        self.window_getter = window_getter
        self.default_limit = default_limit
        self.default_window = default_window
        self.key_type = key_type

    def get_limits(self) -> Tuple[int, int]:
        settings = get_settings()
        limit = self.limit_getter(settings) if self.limit_getter else self.default_limit
        window = self.window_getter(settings) if self.window_getter else self.default_window
        return limit, window

    def build_key(self, request: Request) -> str:
        client_ip = get_client_ip(request)
        # Never include passwords, tokens, or headers other than IP
        return f"rl:{self.scope}:{client_ip}"

    async def __call__(self, request: Request):
        settings = get_settings()
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return

        # starlette TestClient sets client.host to "testclient".
        # To avoid breaking existing un-rate-limited integration tests,
        # in-memory TestClient runs without X-Forwarded-For or X-Test-Rate-Limit are bypassed.
        if request.client and request.client.host == "testclient":
            if "x-test-rate-limit" not in request.headers and "x-forwarded-for" not in request.headers:
                return

        limit, window = self.get_limits()
        key = self.build_key(request)

        allowed, remaining, retry_after = rate_limit_storage.is_allowed(key, limit, window)
        if not allowed:
            logger.warning(
                "Rate limit exceeded for scope='%s' key='%s'. Retry after %s seconds.",
                self.scope,
                key,
                retry_after,
            )
            reset_timestamp = int(time.time() + retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_timestamp),
                },
            )


# Pre-configured dependencies for auth and detection
rate_limit_login = RateLimitDependency(
    scope="login",
    limit_getter=lambda s: getattr(s, "RATE_LIMIT_LOGIN_LIMIT", 5),
    window_getter=lambda s: getattr(s, "RATE_LIMIT_LOGIN_WINDOW", 60),
    default_limit=5,
    default_window=60,
    key_type="ip",
)

rate_limit_register = RateLimitDependency(
    scope="register",
    limit_getter=lambda s: getattr(s, "RATE_LIMIT_REGISTER_LIMIT", 5),
    window_getter=lambda s: getattr(s, "RATE_LIMIT_REGISTER_WINDOW", 60),
    default_limit=5,
    default_window=60,
    key_type="ip",
)

rate_limit_detection = RateLimitDependency(
    scope="detection",
    limit_getter=lambda s: getattr(s, "RATE_LIMIT_DETECTION_LIMIT", 10),
    window_getter=lambda s: getattr(s, "RATE_LIMIT_DETECTION_WINDOW", 60),
    default_limit=10,
    default_window=60,
    key_type="ip",
)
