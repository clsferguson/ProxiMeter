"""Rate limiting middleware using token bucket algorithm.

Protects the API from abuse by limiting mutating operations (POST/PUT/PATCH/DELETE)
per client IP. Read operations (GET) are not rate limited.

Token Bucket Algorithm:
    - Each client has a bucket that fills at a constant rate
    - Bucket has maximum capacity (burst size)
    - Each request consumes 1 token from bucket
    - Request allowed if bucket has ≥1 token
    - Request denied if bucket is empty

Logging Strategy:
    DEBUG - Token bucket operations, exempt path checks
    INFO  - Middleware initialization, configuration
    WARN  - Rate limit violations with client IP

Features:
    - Per-IP rate limiting
    - Burst support for legitimate spikes
    - Health/metrics endpoint exemption
    - Proxy header support (X-Forwarded-For, X-Real-IP)
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Awaitable, Callable, Final

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

# HTTP methods that trigger rate limiting (mutating operations only)
RATE_LIMITED_METHODS: Final[set[str]] = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from rate limiting (health checks, metrics)
EXEMPT_PATHS: Final[set[str]] = {"/health", "/metrics", "/api/health"}

# ============================================================================
# Rate Limit Middleware
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter for API abuse prevention.
    
    Only rate limits mutating operations (POST/PUT/PATCH/DELETE).
    Read operations (GET) are unrestricted for streaming and browsing.
    
    Args:
        app: ASGI application
        requests_per_second: Token refill rate (default: 5.0)
        burst: Maximum token capacity (default: 10)
        
    Example:
        >>> app.add_middleware(
        ...     RateLimitMiddleware,
        ...     requests_per_second=5.0,
        ...     burst=10
        ... )
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_second: float = 5.0,
        burst: int = 10
    ) -> None:
        """Initialize rate limit middleware with token bucket parameters.
        
        Args:
            app: ASGI application
            requests_per_second: Token refill rate (tokens/second)
            burst: Maximum tokens in bucket
        """
        super().__init__(app)
        self.rate = requests_per_second
        self.burst = burst
        
        # Token bucket storage: {client_ip: (tokens, last_update_time)}
        self.buckets: dict[str, tuple[float, float]] = defaultdict(
            lambda: (float(burst), time.time())
        )
        
        logger.info(f"Rate limiter initialized: {requests_per_second} req/s, burst={burst}")
        logger.debug(f"Rate limiting methods: {RATE_LIMITED_METHODS}")
        logger.debug(f"Exempt paths: {EXEMPT_PATHS}")
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response from handler or 429 if rate limited
        """
        # Skip rate limiting for exempt paths (health checks, metrics)
        if request.url.path in EXEMPT_PATHS:
            logger.debug(f"Exempt path: {request.url.path}")
            return await call_next(request)
        
        # Only rate limit mutating methods (POST, PUT, PATCH, DELETE)
        # GET requests are unlimited (needed for streaming)
        if request.method not in RATE_LIMITED_METHODS:
            logger.debug(f"Non-rate-limited method: {request.method}")
            return await call_next(request)
        
        # Check rate limit for this client
        client_ip = self._get_client_ip(request)
        
        if not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded: {client_ip} {request.method} {request.url.path}")
            return self._rate_limit_response()
        
        logger.debug(f"Rate limit OK: {client_ip} {request.method} {request.url.path}")
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.
        
        Handles proxied requests by checking proxy headers first.
        
        Priority:
        1. X-Forwarded-For (standard proxy header)
        2. X-Real-IP (alternative proxy header)
        3. request.client.host (direct connection)
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address or "unknown" if unavailable
        """
        # Check X-Forwarded-For (standard proxy header)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in comma-separated list (original client)
            client_ip = forwarded.split(",")[0].strip()
            logger.debug(f"Client IP from X-Forwarded-For: {client_ip}")
            return client_ip
        
        # Check X-Real-IP (alternative proxy header)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
            logger.debug(f"Client IP from X-Real-IP: {client_ip}")
            return client_ip
        
        # Direct connection
        if request.client:
            logger.debug(f"Client IP from direct connection: {request.client.host}")
            return request.client.host
        
        logger.warning("Unable to determine client IP")
        return "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if request is within rate limit using token bucket.
        
        Token bucket refills at constant rate and caps at burst size.
        Each request consumes 1 token if available.
        
        Args:
            client_ip: Client IP address (rate limit key)
            
        Returns:
            True if request allowed, False if rate limited
        """
        now = time.time()
        tokens, last_update = self.buckets[client_ip]
        
        # Refill tokens based on elapsed time
        elapsed = now - last_update
        refilled_tokens = elapsed * self.rate
        tokens = min(self.burst, tokens + refilled_tokens)
        
        logger.debug(
            f"Token bucket for {client_ip}: {tokens:.2f} tokens "
            f"(refilled {refilled_tokens:.2f} in {elapsed:.2f}s)"
        )
        
        # Check if we have at least 1 token
        if tokens >= 1.0:
            # Consume 1 token and allow request
            self.buckets[client_ip] = (tokens - 1.0, now)
            logger.debug(f"Token consumed: {client_ip} now has {tokens - 1.0:.2f} tokens")
            return True
        
        # Rate limited - no tokens available
        self.buckets[client_ip] = (tokens, now)
        logger.debug(f"Rate limited: {client_ip} has {tokens:.2f} tokens (need 1.0)")
        return False
    
    def _rate_limit_response(self) -> JSONResponse:
        """Generate 429 Too Many Requests response.
        
        Returns:
            JSON response with rate limit error and retry info
        """
        retry_after = int(1.0 / self.rate)  # Seconds to wait for 1 token
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down.",
                "detail": f"Maximum {self.rate} requests per second allowed"
            },
            headers={
                "Retry-After": str(retry_after)
            }
        )


logger.debug("Rate limit middleware module loaded")