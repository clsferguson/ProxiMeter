"""Request ID middleware for distributed tracing and debugging."""
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
    """Middleware to add unique request ID to each request.
    
    Features:
    - Adds X-Request-ID header to requests and responses
    - Supports client-provided request IDs for distributed tracing
    - Stores request ID in request.state for access in handlers
    - Logs request/response with timing information
    
    Usage:
        app.add_middleware(RequestIDMiddleware)
        
        # Access in route handler:
        @app.get("/")
        async def handler(request: Request):
            request_id = request.state.request_id
            logger.info(f"Processing request {request_id}")
    """
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",
        log_requests: bool = True
    ) -> None:
        """Initialize request ID middleware.
        
        Args:
            app: ASGI application
            header_name: HTTP header name for request ID (default: X-Request-ID)
            log_requests: Whether to log request/response (default: True)
        """
        super().__init__(app)
        self.header_name = header_name
        self.log_requests = log_requests
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and inject request ID.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response with X-Request-ID header
        """
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = self._generate_request_id()
        
        # Store in request state for access in handlers
        request.state.request_id = request_id
        
        # Start timing (always, so duration is available)
        start_time = time.time()

        # Log incoming request
        if self.log_requests:
            self._log_request(request, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.header_name] = request_id
            
            # Log response
            if self.log_requests:
                duration = time.time() - start_time
                self._log_response(request, response, request_id, duration)
            
            return response
            
        except Exception as e:
            # Log exception with request ID
            logger.error(
                f"Request {request_id} failed: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"request_id": request_id}
            )
            raise
    
    def _generate_request_id(self) -> str:
        """Generate a new request ID.
        
        Uses UUID4 for guaranteed uniqueness across distributed systems.
        
        Returns:
            UUID string (e.g., "550e8400-e29b-41d4-a716-446655440000")
        """
        return str(uuid.uuid4())
    
    def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request details.
        
        Args:
            request: HTTP request
            request_id: Request ID
        """
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration: float
    ) -> None:
        """Log response details with timing.
        
        Args:
            request: HTTP request
            response: HTTP response
            request_id: Request ID
            duration: Request duration in seconds
        """
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        logger.log(
            log_level,
            f"← {request.method} {request.url.path} {response.status_code} ({duration*1000:.2f}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        )


# ============================================================================
# Context Filter for Logging
# ============================================================================

class RequestIDFilter(logging.Filter):
    """Logging filter that adds request_id to all log records.
    
    Extracts request_id from contextvars or log record extras.
    Useful for correlating logs across multiple handlers.
    
    Usage:
        logger = logging.getLogger()
        logger.addFilter(RequestIDFilter())
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to log record if not present.
        
        Args:
            record: Log record to filter
            
        Returns:
            True (always include record)
        """
        # Add request_id if not already present
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "request_id", "-")
        
        return True


# ============================================================================
# Helper Functions
# ============================================================================

def get_request_id(request: Request) -> str | None:
    """Get request ID from request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        Request ID or None if not available
        
    Example:
        >>> from fastapi import Request
        >>> 
        >>> @app.get("/")
        >>> async def handler(request: Request):
        ...     request_id = get_request_id(request)
        ...     logger.info(f"Processing {request_id}")
    """
    return getattr(request.state, "request_id", None)
