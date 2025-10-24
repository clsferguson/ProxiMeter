"""Standardized error handling and response schemas."""
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
    
    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional error context
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
    
    Using Enum ensures type safety and prevents typos.
    """
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE_NAME = "DUPLICATE_NAME"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_RTSP_URL = "INVALID_RTSP_URL"
    INVALID_ORDER = "INVALID_ORDER"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    
    # Operation errors
    STREAM_NOT_RUNNING = "STREAM_NOT_RUNNING"
    STREAM_ALREADY_RUNNING = "STREAM_ALREADY_RUNNING"
    MAX_STREAMS_REACHED = "MAX_STREAMS_REACHED"
    
    # System errors
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
    
    Args:
        code: Error code (preferably from ErrorCode enum)
        message: Human-readable error message
        details: Optional additional error context
        
    Returns:
        Structured error response
    """
    if isinstance(code, ErrorCode):
        code = code.value
    
    return ErrorResponse(code=code, message=message, details=details)


# ============================================================================
# Specialized Error Raisers
# ============================================================================

def raise_not_found(resource: str, resource_id: str) -> None:
    """Raise a standardized 404 error.
    
    Args:
        resource: Resource type (e.g., "stream", "zone")
        resource_id: Resource identifier
        
    Raises:
        HTTPException: 404 error with standardized format
        
    Example:
        raise_not_found("stream", "550e8400-e29b-41d4-a716-446655440000")
    """
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
    
    Args:
        message: Error message
        details: Optional validation details
        
    Raises:
        HTTPException: 400 error with standardized format
    """
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
    
    Args:
        resource: Resource type
        name: Duplicate name
        
    Raises:
        HTTPException: 400 error with standardized format
    """
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
    
    Args:
        url: Invalid RTSP URL
        reason: Specific reason for invalidity
        
    Raises:
        HTTPException: 400 error with standardized format
    """
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
    
    Args:
        message: Error message
        details: Optional conflict details
        
    Raises:
        HTTPException: 409 error with standardized format
    """
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
    
    Args:
        message: Error message
        details: Optional service details
        
    Raises:
        HTTPException: 503 error with standardized format
    """
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
    
    Args:
        request: FastAPI request
        exc: Validation error exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc.errors()}"
    )
    
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
    
    Args:
        request: FastAPI request
        exc: HTTP exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # If detail is already in our standardized format, use it
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, wrap in standard format
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
    
    Logs the full exception traceback and returns a generic error message
    to avoid leaking sensitive information.
    
    Args:
        request: FastAPI request
        exc: Unhandled exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}",
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
    
    Args:
        data: Response data to check
        
    Returns:
        True if data matches error response structure
    """
    return (
        isinstance(data, dict)
        and "code" in data
        and "message" in data
    )
