"""Shared Redis-backed API rate limiting; production fails closed if Redis is unavailable."""
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url, general_limit=120, sensitive_limit=20, invite_limit=10):
        super().__init__(app)
        self.redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        self.general_limit = general_limit
        self.sensitive_limit = sensitive_limit
        self.invite_limit = invite_limit

    async def dispatch(self, request, call_next):
        if request.url.path in {"/api/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        if self.redis is None:
            return await call_next(request)
        # Use the socket peer address. Do not trust caller-controlled X-Forwarded-For.
        peer = request.client.host if request.client else "unknown"
        path = request.url.path
        sensitive = path.startswith(("/api/chat", "/api/checkins", "/api/caregivers", "/api/caregiver"))
        limit = self.sensitive_limit if sensitive else self.general_limit
        window = 60
        key = f"ur-chart:rate:{peer}:{'sensitive' if sensitive else 'general'}:{int(__import__('time').time()) // window}"
        try:
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window + 5)
            count, _ = await pipe.execute()
            if path == "/api/caregivers/invitations" and request.method == "POST":
                hour_key = f"ur-chart:invite:{peer}:{int(__import__('time').time()) // 3600}"
                invite_pipe = self.redis.pipeline()
                invite_pipe.incr(hour_key)
                invite_pipe.expire(hour_key, 3605)
                invite_count, _ = await invite_pipe.execute()
                if invite_count > self.invite_limit:
                    return JSONResponse(status_code=429, content={"error":{"code":"rate_limit_exceeded","message":"Too many caregiver invitations. Try again later."}}, headers={"Retry-After":"3600"})
            if count > limit:
                return JSONResponse(status_code=429, content={"error":{"code":"rate_limit_exceeded","message":"Too many requests. Try again later."}}, headers={"Retry-After":"60"})
        except RedisError:
            return JSONResponse(status_code=503, content={"error":{"code":"rate_limiter_unavailable","message":"Request protection is temporarily unavailable."}})
        return await call_next(request)
