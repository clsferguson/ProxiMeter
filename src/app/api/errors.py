"""API error schemas and standardized error responses."""
from pydantic import BaseModel, ValidationError
from typing import Optional, Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ErrorCode:
    """Standard error codes for the API."""
    
    INVALID_RTSP_URL = "INVALID_RTSP_URL"
    DUPLICATE_NAME = "DUPLICATE_NAME"
    INVALID_ORDER = "INVALID_ORDER"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def create_error_response(code: str, message: str, details: Optional[dict] = None) -> ErrorResponse:
    """Create a standardized error response.
    
    Args:
        code: Error code from ErrorCode class
        message: Human-readable error message
        details: Optional additional details
        
    Returns:
        ErrorResponse object
    """
    return ErrorResponse(code=code, message=message, details=details)


def raise_not_found(resource: str, resource_id: str) -> None:
    """Raise a 404 error with standard format.
    
    Args:
        resource: Resource type (e.g., "stream")
        resource_id: Resource identifier
        
    Raises:
        HTTPException: 404 error
    """
    error = create_error_response(
        code=ErrorCode.NOT_FOUND,
        message=f"{resource.capitalize()} not found",
        details={"id": resource_id}
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error.model_dump()
    )


def raise_validation_error(message: str, details: Optional[dict] = None) -> None:
    """Raise a 400 validation error with standard format.
    
    Args:
        message: Error message
        details: Optional validation details
        
    Raises:
        HTTPException: 400 error
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


def raise_duplicate_name(name: str) -> None:
    """Raise a 400 error for duplicate stream name.
    
    Args:
        name: Duplicate stream name
        
    Raises:
        HTTPException: 400 error
    """
    error = create_error_response(
        code=ErrorCode.DUPLICATE_NAME,
        message=f"Stream name '{name}' already exists (case-insensitive)",
        details={"name": name}
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error.model_dump()
    )


def raise_invalid_rtsp_url(url: str, reason: str = "Invalid RTSP URL format") -> None:
    """Raise a 400 error for invalid RTSP URL.
    
    Args:
        url: Invalid RTSP URL
        reason: Reason for invalidity
        
    Raises:
        HTTPException: 400 error
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


def raise_invalid_order(message: str, details: Optional[dict] = None) -> None:
    """Raise a 400 error for invalid reorder request.
    
    Args:
        message: Error message
        details: Optional details about the invalid order
        
    Raises:
        HTTPException: 400 error
    """
    error = create_error_response(
        code=ErrorCode.INVALID_ORDER,
        message=message,
        details=details
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with standardized format.
    
    Args:
        request: FastAPI request
        exc: Validation error exception
        
    Returns:
        JSONResponse with standardized error format
    """
    error = create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details={"errors": exc.errors()}
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException with standardized format.
    
    Args:
        request: FastAPI request
        exc: HTTP exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # If detail is already in our format (dict with code/message), use it
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


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standardized format.
    
    Args:
        request: FastAPI request
        exc: Unhandled exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.exception("Unhandled exception", exc_info=exc)
    
    error = create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.model_dump()
    )
