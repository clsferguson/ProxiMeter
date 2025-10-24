"""Lightweight rate limiting middleware for mutating routes."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple token bucket rate limiter for mutating HTTP methods.
    
    Applies rate limiting to POST, PUT, PATCH, DELETE requests only.
    Uses client IP as the key for rate limiting.
    
    Args:
        app: FastAPI application
        requests_per_second: Maximum requests per second per client (default: 5)
        burst: Maximum burst size (default: 10)
    """
    
    def __init__(
        self,
        app,
        requests_per_second: float = 5.0,
        burst: int = 10
    ):
        super().__init__(app)
        self.rate = requests_per_second
        self.burst = burst
        
        # Token bucket storage: {client_ip: (tokens, last_update_time)}
        self.buckets: dict[str, tuple[float, float]] = defaultdict(
            lambda: (float(burst), time.time())
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address
        """
        # Try X-Forwarded-For first (if behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if request is within rate limit using token bucket algorithm.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        tokens, last_update = self.buckets[client_ip]
        
        # Refill tokens based on time elapsed
        elapsed = now - last_update
        tokens = min(self.burst, tokens + elapsed * self.rate)
        
        # Check if we have at least 1 token
        if tokens >= 1.0:
            # Consume 1 token
            self.buckets[client_ip] = (tokens - 1.0, now)
            return True
        else:
            # Rate limited
            self.buckets[client_ip] = (tokens, now)
            return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler or rate limit error
        """
        path = request.url.path
        # Exempt /mjpeg and /health endpoints from rate limiting
        if path.startswith("/streams/") and "/mjpeg" in path or path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Only rate limit mutating methods
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            client_ip = self._get_client_ip(request)
            
            if not self._check_rate_limit(client_ip):
                logger.warning(
                    f"Rate limit exceeded for {client_ip} on {request.method} {request.url.path}"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down."
                    }
                )
        
        # Process request
        response = await call_next(request)
        return response
