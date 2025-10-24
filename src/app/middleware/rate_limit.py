"""Rate limiting middleware using token bucket algorithm."""
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

# HTTP methods that trigger rate limiting
RATE_LIMITED_METHODS: Final[set[str]] = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from rate limiting
EXEMPT_PATHS: Final[set[str]] = {"/health", "/metrics", "/api/health"}


# ============================================================================
# Rate Limit Middleware
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter for mutating HTTP requests.
    
    Features:
    - Applies only to POST, PUT, PATCH, DELETE methods
    - Uses client IP address as rate limit key
    - Token bucket algorithm for smooth rate limiting
    - Exempts health/metrics endpoints
    - Supports X-Forwarded-For for proxy scenarios
    
    Token Bucket Algorithm:
        - Each client has a bucket with a maximum capacity (burst)
        - Tokens are added to bucket at a constant rate
        - Each request consumes 1 token
        - Request is allowed if bucket has ≥1 token
    
    Args:
        app: ASGI application
        requests_per_second: Token refill rate (default: 5.0)
        burst: Maximum bucket capacity (default: 10)
        
    Example:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_second=5.0,
            burst=10
        )
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_second: float = 5.0,
        burst: int = 10
    ) -> None:
        """Initialize rate limit middleware.
        
        Args:
            app: ASGI application
            requests_per_second: Maximum requests per second per client
            burst: Maximum burst size (tokens in bucket)
        """
        super().__init__(app)
        self.rate = requests_per_second
        self.burst = burst
        
        # Token bucket storage: {client_ip: (tokens, last_update_time)}
        self.buckets: dict[str, tuple[float, float]] = defaultdict(
            lambda: (float(burst), time.time())
        )
        
        logger.info(
            f"Rate limiter initialized: {requests_per_second} req/s, burst={burst}"
        )
    
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
            Response from handler or 429 rate limit error
        """
        # Check if path is exempt
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Only rate limit mutating methods
        if request.method not in RATE_LIMITED_METHODS:
            return await call_next(request)
        
        # Check rate limit
        client_ip = self._get_client_ip(request)
        
        if not self._check_rate_limit(client_ip):
            logger.warning(
                f"Rate limit exceeded: {client_ip} {request.method} {request.url.path}"
            )
            return self._rate_limit_response()
        
        # Process request
        return await call_next(request)
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from rate limiting.
        
        Args:
            path: Request path
            
        Returns:
            True if path is exempt
        """
        # Check exact match
        if path in EXEMPT_PATHS:
            return True
        
        # Check for MJPEG streaming endpoints
        if "/mjpeg" in path:
            return True
        
        return False
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.
        
        Handles proxied requests by checking X-Forwarded-For header.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address or "unknown" if unavailable
        """
        # Try X-Forwarded-For first (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in comma-separated list
            return forwarded.split(",")[0].strip()
        
        # Try X-Real-IP (alternative proxy header)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if request is within rate limit using token bucket.
        
        Token Bucket Algorithm:
        1. Calculate elapsed time since last request
        2. Add tokens based on: elapsed_time * rate
        3. Cap tokens at burst size
        4. If tokens ≥ 1, consume 1 token and allow request
        5. Otherwise, deny request
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if request allowed, False if rate limited
        """
        now = time.time()
        tokens, last_update = self.buckets[client_ip]
        
        # Calculate elapsed time and refill tokens
        elapsed = now - last_update
        tokens = min(self.burst, tokens + elapsed * self.rate)
        
        # Check if we have at least 1 token
        if tokens >= 1.0:
            # Consume 1 token and allow request
            self.buckets[client_ip] = (tokens - 1.0, now)
            return True
        
        # Rate limited - no tokens available
        self.buckets[client_ip] = (tokens, now)
        return False
    
    def _rate_limit_response(self) -> JSONResponse:
        """Generate 429 Too Many Requests response.
        
        Returns:
            JSON response with rate limit error
        """
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down.",
                "detail": f"Maximum {self.rate} requests per second allowed"
            },
            headers={
                "Retry-After": str(int(1 / self.rate))  # Seconds to wait
            }
        )
