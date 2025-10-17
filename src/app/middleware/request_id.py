"""Request ID middleware for tracing requests."""
from __future__ import annotations

import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request.
    
    Adds X-Request-ID header to both request context and response.
    If client provides X-Request-ID, it will be used; otherwise generates new UUID.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response with X-Request-ID header
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state for access in handlers/logging
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
