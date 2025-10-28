"""Request ID middleware for distributed tracing and request correlation.

Assigns a unique identifier (UUID4) to each request for tracking across logs,
services, and debugging. Supports client-provided request IDs for distributed
tracing scenarios (e.g., microservices, API gateways).

Logging Strategy:
    DEBUG - Request ID generation, client-provided IDs
    INFO  - Request start (→) with method and path
    INFO  - Successful responses (← 2xx/3xx) with duration
    WARN  - Client errors (4xx) with duration
    ERROR - Server errors (5xx) with duration
    ERROR - Unhandled exceptions with stack trace

Features:
    - UUID4 request IDs for guaranteed uniqueness
    - Client-provided ID support (distributed tracing)
    - Request/response logging with timing
    - Stores ID in request.state for handler access
    - Adds X-Request-ID header to responses
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# ============================================================================
# Request ID Middleware
# ============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request for tracing.
    
    Automatically generates UUID4 request IDs or accepts client-provided IDs
    via X-Request-ID header. Logs all requests/responses with timing.
    
    Args:
        app: ASGI application
        header_name: HTTP header name for request ID (default: X-Request-ID)
        
    Usage:
        >>> app.add_middleware(RequestIDMiddleware)
        >>> 
        >>> @app.get("/")
        >>> async def handler(request: Request):
        ...     request_id = request.state.request_id
        ...     logger.info(f"Processing {request_id}")
    """
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID"
    ) -> None:
        """Initialize request ID middleware.
        
        Args:
            app: ASGI application
            header_name: HTTP header name for request ID
        """
        super().__init__(app)
        self.header_name = header_name
        logger.info(f"Request ID middleware initialized with header: {header_name}")
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with unique request ID.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response with X-Request-ID header
        """
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if request_id:
            logger.debug(f"Using client-provided request ID: {request_id}")
        else:
            request_id = self._generate_request_id()
            logger.debug(f"Generated request ID: {request_id}")
        
        # Store in request state for handler access
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log incoming request
        self._log_request(request, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.header_name] = request_id
            
            # Log response with timing
            duration = time.time() - start_time
            self._log_response(request, response, request_id, duration)
            
            return response
            
        except Exception as e:
            # Log exception with request ID and stack trace
            duration = time.time() - start_time
            logger.error(
                f"Request {request_id} failed after {duration*1000:.2f}ms: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
                extra={"request_id": request_id}
            )
            raise
    
    def _generate_request_id(self) -> str:
        """Generate a new request ID using UUID4.
        
        UUID4 provides guaranteed uniqueness across distributed systems
        without coordination or central authority.
        
        Returns:
            UUID string (36 chars, e.g., "550e8400-e29b-41d4-a716-446655440000")
        """
        return str(uuid.uuid4())
    
    def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request with method and path.
        
        Args:
            request: HTTP request
            request_id: Request ID for correlation
        """
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration: float
    ) -> None:
        """Log response with status code and timing.
        
        Log level varies by status code:
        - 2xx/3xx: INFO (success)
        - 4xx: WARN (client error)
        - 5xx: ERROR (server error)
        
        Args:
            request: HTTP request
            response: HTTP response
            request_id: Request ID for correlation
            duration: Request duration in seconds
        """
        # Determine log level based on status code
        status = response.status_code
        if status >= 500:
            log_level = logging.ERROR
        elif status >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        duration_ms = duration * 1000
        
        logger.log(
            log_level,
            f"← {request.method} {request.url.path} {status} ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "status_code": status,
                "duration_ms": round(duration_ms, 2)
            }
        )


# ============================================================================
# Helper Functions
# ============================================================================

def get_request_id(request: Request) -> str | None:
    """Get request ID from request state.
    
    Helper function for accessing request ID in route handlers.
    
    Args:
        request: FastAPI request
        
    Returns:
        Request ID or None if middleware not active
        
    Example:
        >>> @app.get("/example")
        >>> async def handler(request: Request):
        ...     request_id = get_request_id(request)
        ...     logger.info(f"Processing request {request_id}")
    """
    return getattr(request.state, "request_id", None)


logger.debug("Request ID middleware module loaded")
