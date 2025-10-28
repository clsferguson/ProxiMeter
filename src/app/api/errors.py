"""Standardized error handling and response schemas for REST API.

This module provides consistent error handling across all API endpoints with:
- Standardized error response format
- Type-safe error codes (Enum)
- Convenient error raiser functions
- Global exception handlers for FastAPI
- Request validation error formatting

Error Response Format:
    All errors return JSON with this structure:
    {
        "code": "NOT_FOUND",
        "message": "Human-readable description",
        "details": {"additional": "context"}
    }

Error Categories:
    - Resource errors: NOT_FOUND, DUPLICATE_NAME, RESOURCE_CONFLICT
    - Validation errors: VALIDATION_ERROR, INVALID_RTSP_URL
    - Operation errors: STREAM_NOT_RUNNING, STREAM_ALREADY_RUNNING
    - System errors: INTERNAL_ERROR, SERVICE_UNAVAILABLE

Logging Strategy:
    DEBUG - Error creation, response formatting
    INFO  - Successful error handling (recovery)
    WARN  - Validation errors, client errors (4xx)
    ERROR - Server errors (5xx), unexpected exceptions

Usage:
    # Raise specific errors
    >>> raise_not_found("stream", stream_id)
    >>> raise_validation_error("Name is required")
    
    # Create custom errors
    >>> error = create_error_response(ErrorCode.NOT_FOUND, "Not found")
    >>> raise HTTPException(404, detail=error.model_dump())
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============================================================================
# Error Response Schema
# ============================================================================

class ErrorResponse(BaseModel):
    """Standardized error response schema for all API errors.
    
    Provides consistent structure for error responses across all endpoints.
    Enables clients to handle errors programmatically using error codes.
    
    Attributes:
        code: Machine-readable error code (from ErrorCode enum)
        message: Human-readable error message for display
        details: Optional additional context (dict with arbitrary fields)
    
    Example:
        {
            "code": "NOT_FOUND",
            "message": "Stream not found",
            "details": {"id": "550e8400-e29b-41d4-a716-446655440000"}
        }
    """
    
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "NOT_FOUND",
                    "message": "Stream not found",
                    "details": {"id": "550e8400-e29b-41d4-a716-446655440000"}
                }
            ]
        }
    }


# ============================================================================
# Error Codes Enum
# ============================================================================

class ErrorCode(str, Enum):
    """Standardized error codes for the API.
    
    Using Enum ensures:
    - Type safety (Pylance/mypy catches typos)
    - Autocomplete in IDEs
    - Consistent codes across codebase
    - Easy to document all possible errors
    """
    
    # Resource errors (404, 409)
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE_NAME = "DUPLICATE_NAME"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Validation errors (400, 422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_RTSP_URL = "INVALID_RTSP_URL"
    INVALID_ORDER = "INVALID_ORDER"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    
    # Operation errors (400, 409)
    STREAM_NOT_RUNNING = "STREAM_NOT_RUNNING"
    STREAM_ALREADY_RUNNING = "STREAM_ALREADY_RUNNING"
    MAX_STREAMS_REACHED = "MAX_STREAMS_REACHED"
    
    # System errors (500, 503)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# ============================================================================
# Error Response Factory
# ============================================================================

def create_error_response(
    code: ErrorCode | str,
    message: str,
    details: Optional[dict[str, Any]] = None
) -> ErrorResponse:
    """Create a standardized error response.
    
    Factory function for creating consistent error responses.
    Automatically converts ErrorCode enum to string value.
    
    Args:
        code: Error code (ErrorCode enum or string)
        message: Human-readable error message
        details: Optional additional error context
        
    Returns:
        Structured ErrorResponse object
        
    Example:
        >>> error = create_error_response(
        ...     ErrorCode.NOT_FOUND,
        ...     "Stream not found",
        ...     {"id": stream_id}
        ... )
        
    Logs:
        DEBUG: Error response creation
    """
    if isinstance(code, ErrorCode):
        code_str = code.value
    else:
        code_str = code
    
    logger.debug(f"Creating error response: code={code_str}, message={message}")
    
    return ErrorResponse(code=code_str, message=message, details=details)


# ============================================================================
# Specialized Error Raisers
# ============================================================================

def raise_not_found(resource: str, resource_id: str) -> None:
    """Raise a standardized 404 error.
    
    Used when a requested resource doesn't exist.
    
    Args:
        resource: Resource type (e.g., "stream", "zone")
        resource_id: Resource identifier
        
    Raises:
        HTTPException: 404 error with standardized format
        
    Example:
        >>> raise_not_found("stream", "550e8400-e29b-41d4-a716-446655440000")
        
    Logs:
        DEBUG: Resource not found details
    """
    logger.debug(f"Resource not found: {resource} with id={resource_id}")
    
    error = create_error_response(
        code=ErrorCode.NOT_FOUND,
        message=f"{resource.capitalize()} not found",
        details={"resource": resource, "id": resource_id}
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error.model_dump()
    )


def raise_validation_error(
    message: str,
    details: Optional[dict[str, Any]] = None
) -> None:
    """Raise a standardized 400 validation error.
    
    Used for business logic validation failures that aren't
    caught by Pydantic schema validation.
    
    Args:
        message: Error message
        details: Optional validation details
        
    Raises:
        HTTPException: 400 error with standardized format
        
    Example:
        >>> raise_validation_error("Name must be unique", {"name": "Camera 1"})
        
    Logs:
        DEBUG: Validation error details
    """
    logger.debug(f"Validation error: {message}, details={details}")
    
    error = create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=details
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error.model_dump()
    )


def raise_duplicate_name(resource: str, name: str) -> None:
    """Raise a standardized error for duplicate resource names.
    
    Used when attempting to create or rename a resource with an
    already-existing name.
    
    Args:
        resource: Resource type
        name: Duplicate name
        
    Raises:
        HTTPException: 400 error with standardized format
        
    Example:
        >>> raise_duplicate_name("stream", "Front Door Camera")
        
    Logs:
        DEBUG: Duplicate name error details
    """
    logger.debug(f"Duplicate {resource} name: '{name}'")
    
    error = create_error_response(
        code=ErrorCode.DUPLICATE_NAME,
        message=f"{resource.capitalize()} name '{name}' already exists",
        details={"resource": resource, "name": name}
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error.model_dump()
    )


def raise_invalid_rtsp_url(
    url: str,
    reason: str = "Invalid RTSP URL format"
) -> None:
    """Raise a standardized error for invalid RTSP URLs.
    
    Used when RTSP URL fails validation (schema, format, etc).
    
    Args:
        url: Invalid RTSP URL
        reason: Specific reason for invalidity
        
    Raises:
        HTTPException: 400 error with standardized format
        
    Example:
        >>> raise_invalid_rtsp_url("http://camera", "Must use rtsp:// scheme")
        
    Logs:
        DEBUG: Invalid RTSP URL details (URL is logged)
    """
    logger.debug(f"Invalid RTSP URL: {url}, reason: {reason}")
    
    error = create_error_response(
        code=ErrorCode.INVALID_RTSP_URL,
        message=reason,
        details={"rtsp_url": url}
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error.model_dump()
    )


def raise_conflict(
    message: str,
    details: Optional[dict[str, Any]] = None
) -> None:
    """Raise a standardized 409 conflict error.
    
    Used when an operation conflicts with current system state.
    Examples: starting an already-running stream, deleting a locked resource.
    
    Args:
        message: Error message
        details: Optional conflict details
        
    Raises:
        HTTPException: 409 error with standardized format
        
    Example:
        >>> raise_conflict("Stream is already running", {"id": stream_id})
        
    Logs:
        DEBUG: Conflict error details
    """
    logger.debug(f"Resource conflict: {message}, details={details}")
    
    error = create_error_response(
        code=ErrorCode.RESOURCE_CONFLICT,
        message=message,
        details=details
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=error.model_dump()
    )


def raise_service_unavailable(
    message: str = "Service temporarily unavailable",
    details: Optional[dict[str, Any]] = None
) -> None:
    """Raise a standardized 503 service unavailable error.
    
    Used when service dependencies are down or system is overloaded.
    Examples: GPU unavailable, FFmpeg process limit reached.
    
    Args:
        message: Error message
        details: Optional service details
        
    Raises:
        HTTPException: 503 error with standardized format
        
    Example:
        >>> raise_service_unavailable("GPU not available", {"backend": "none"})
        
    Logs:
        WARN: Service unavailable condition
    """
    logger.warning(f"Service unavailable: {message}, details={details}")
    
    error = create_error_response(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=message,
        details=details
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=error.model_dump()
    )


# ============================================================================
# Global Exception Handlers
# ============================================================================

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with standardized format.
    
    Catches request body validation failures and formats them consistently.
    Called automatically by FastAPI for RequestValidationError exceptions.
    
    Args:
        request: FastAPI request object
        exc: Validation error exception
        
    Returns:
        JSONResponse with standardized error format (422 status)
        
    Logs:
        WARN: Validation errors (client-side issue)
        DEBUG: Full validation error details
    """
    error_count = len(exc.errors())
    logger.warning(
        f"Validation failed: {request.method} {request.url.path} "
        f"({error_count} error(s))"
    )
    logger.debug(f"Validation errors: {exc.errors()}")
    
    error = create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details={
            "errors": exc.errors(),
            "body": str(exc.body) if exc.body else None
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error.model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handle HTTPException with standardized format.
    
    Catches explicitly raised HTTPException instances and formats them.
    If already in standardized format, passes through. Otherwise, wraps.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        JSONResponse with standardized error format
        
    Logs:
        INFO: Client errors (4xx) - expected behavior
        ERROR: Server errors (5xx) - unexpected issues
    """
    # Log based on status code severity
    if exc.status_code >= 500:
        logger.error(
            f"Server error: {request.method} {request.url.path} "
            f"-> {exc.status_code}: {exc.detail}"
        )
    else:
        logger.info(
            f"Client error: {request.method} {request.url.path} "
            f"-> {exc.status_code}: {exc.detail}"
        )
    
    # If detail is already in our standardized format, use it
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        logger.debug("Using pre-formatted error response")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, wrap in standard format
    logger.debug("Wrapping HTTPException in standard format")
    error = create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message=str(exc.detail) if exc.detail else "An error occurred"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump()
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions with standardized format.
    
    Catches all unhandled exceptions and formats them consistently.
    Logs full stack trace for debugging but returns generic message
    to avoid leaking sensitive information to clients.
    
    Args:
        request: FastAPI request object
        exc: Unhandled exception
        
    Returns:
        JSONResponse with standardized error format (500 status)
        
    Logs:
        ERROR: Full exception with stack trace
    """
    logger.error(
        f"Unhandled exception: {request.method} {request.url.path} "
        f"-> {type(exc).__name__}: {str(exc)}",
        exc_info=exc
    )
    
    error = create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal server error occurred"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.model_dump()
    )


# ============================================================================
# Convenience Functions
# ============================================================================

def is_error_response(data: Any) -> bool:
    """Check if a response is an error response.
    
    Useful for testing and client-side error detection.
    
    Args:
        data: Response data to check
        
    Returns:
        True if data matches error response structure
        
    Example:
        >>> response = {"code": "NOT_FOUND", "message": "Not found"}
        >>> is_error_response(response)
        True
        
    Logs:
        DEBUG: Error response detection result
    """
    result = (
        isinstance(data, dict)
        and "code" in data
        and "message" in data
    )
    
    logger.debug(f"Error response check: {result} for data keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
    
    return result


# Log module initialization
logger.debug("Error handling module initialized")
