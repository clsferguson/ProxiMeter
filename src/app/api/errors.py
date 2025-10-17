"""API error schemas and standardized error responses."""
from pydantic import BaseModel
from typing import Optional, Any
from fastapi import HTTPException, status


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
