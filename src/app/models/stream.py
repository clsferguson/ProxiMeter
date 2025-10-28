"""Stream data models for ProxiMeter.

Defines Pydantic v2 models for RTSP stream configuration:
- Stream: Complete stream with all fields (used in responses)
- NewStream: Stream creation (excludes auto-generated fields)
- EditStream: Partial updates (all fields optional, PATCH semantics)
- ReorderRequest: Reorder streams in UI

Field Validation:
- RTSP URL must start with rtsp:// or rtsps://
- Name length: 1-50 characters
- No duplicate stream IDs in reorder requests

Constitution Compliance:
- auto_start: Resume streams on application restart
- hw_accel_enabled: GPU-only operation enforcement
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ============================================================================
# Validation Helpers
# ============================================================================

def validate_rtsp_url(url: str) -> None:
    """Validate RTSP URL protocol prefix.
    
    Args:
        url: RTSP URL to validate
        
    Raises:
        ValueError: If URL doesn't start with rtsp:// or rtsps://
    """
    if not url.startswith(("rtsp://", "rtsps://")):
        raise ValueError("RTSP URL must start with rtsp:// or rtsps://")


# ============================================================================
# Complete Stream Model
# ============================================================================

class Stream(BaseModel):
    """Complete stream model with all fields.
    
    Represents a fully-configured RTSP stream for GPU-accelerated processing.
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique stream identifier (UUID)"
    )
    
    name: str = Field(
        min_length=1,
        max_length=50,
        description="Human-readable stream name",
        examples=["Front Door Camera", "Parking Lot"]
    )
    
    rtsp_url: str = Field(
        min_length=10,
        description="RTSP stream URL",
        examples=["rtsp://admin:pass@192.168.1.100:554/stream"]
    )
    
    ffmpeg_params: list[str] = Field(
        default_factory=list,
        description="Custom FFmpeg parameters (empty uses defaults)"
    )
    
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp"
    )
    
    order: int = Field(
        default=0,
        ge=0,
        description="Display order in UI (0-based)"
    )
    
    status: Literal["running", "stopped"] = Field(
        default="stopped",
        description="Current processing status"
    )
    
    @model_validator(mode="after")
    def validate_rtsp_url_format(self) -> Stream:
        """Validate RTSP URL protocol."""
        validate_rtsp_url(self.rtsp_url)
        return self


# ============================================================================
# Stream Creation Model
# ============================================================================

class NewStream(BaseModel):
    """Model for creating new streams.
    
    Excludes auto-generated fields (id, created_at, order, status).
    """
    
    name: str = Field(
        min_length=1,
        max_length=50,
        description="Human-readable stream name",
        examples=["Front Door Camera", "Parking Lot"]
    )
    
    rtsp_url: str = Field(
        min_length=10,
        description="RTSP stream URL",
        examples=["rtsp://admin:pass@192.168.1.100:554/stream"]
    )
    
    ffmpeg_params: list[str] = Field(
        default_factory=list,
        description="Custom FFmpeg parameters (empty uses defaults)"
    )
    
    @model_validator(mode="after")
    def validate_rtsp_url_format(self) -> NewStream:
        """Validate RTSP URL protocol."""
        validate_rtsp_url(self.rtsp_url)
        return self


# ============================================================================
# Stream Update Model
# ============================================================================

class EditStream(BaseModel):
    """Model for partial stream updates (PATCH semantics).
    
    All fields optional - only provided fields are updated.
    """
    
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Human-readable stream name"
    )
    
    rtsp_url: str | None = Field(
        default=None,
        min_length=10,
        description="RTSP stream URL"
    )
    
    status: Literal["running", "stopped"] | None = Field(
        default=None,
        description="Processing status"
    )
    
    ffmpeg_params: list[str] | None = Field(
        default=None,
        description="Custom FFmpeg parameters"
    )
    
    @model_validator(mode="after")
    def validate_rtsp_url_format(self) -> EditStream:
        """Validate RTSP URL protocol if provided."""
        if self.rtsp_url is not None:
            validate_rtsp_url(self.rtsp_url)
        return self


# ============================================================================
# Stream Reordering Model
# ============================================================================

class ReorderRequest(BaseModel):
    """Model for reordering streams in the UI.
    
    Ordered list of stream IDs (UUIDs) representing new display order.
    """
    
    order: list[str] = Field(
        min_length=1,
        description="Ordered list of stream IDs",
        examples=[
            ["uuid-1", "uuid-2", "uuid-3"],
            ["550e8400-e29b-41d4-a716-446655440000"]
        ]
    )
    
    @model_validator(mode="after")
    def validate_no_duplicates(self) -> ReorderRequest:
        """Validate no duplicate stream IDs."""
        if len(self.order) != len(set(self.order)):
            raise ValueError("Order list contains duplicate stream IDs")
        return self
