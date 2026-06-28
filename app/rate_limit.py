import time
from collections import defaultdict
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class Bucket:
    tokens: float
    last_refill: float


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory token bucket per API key (portfolio demo; use Redis in production)."""

    def __init__(self, app, rate: float = 10.0, burst: float = 20.0):
        super().__init__(app)
        self.rate = rate
        self.burst = burst
        self._buckets: dict[str, Bucket] = defaultdict(lambda: Bucket(tokens=burst, last_refill=time.monotonic()))

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "anonymous")
        now = time.monotonic()
        bucket = self._buckets[api_key]
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
        bucket.last_refill = now

        if bucket.tokens < 1:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "1"},
            )
        bucket.tokens -= 1
        return await call_next(request)
