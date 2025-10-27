"""Stream data models for ProxiMeter.

Defines Pydantic models for RTSP stream configuration and management:
- Stream: Complete stream model with all fields
- NewStream: Model for creating new streams (without generated fields)
- EditStream: Model for partial stream updates (all fields optional)
- ReorderRequest: Model for reordering streams in the UI

All models use Pydantic v2 with type annotations and field validation.

Updated: Added auto_start field to enable automatic stream startup on
creation and application restart.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Complete Stream Model
# ============================================================================

class Stream(BaseModel):
    """Complete stream model with all fields.
    
    Represents a fully-configured RTSP stream with processing parameters.
    """
    
    id: Annotated[
        str,
        Field(
            default_factory=lambda: str(uuid.uuid4()),
            description="Unique stream identifier (UUID)"
        )
    ]
    
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Human-readable stream name",
            examples=["Front Door Camera", "Parking Lot"]
        )
    ]
    
    rtsp_url: Annotated[
        str,
        Field(
            min_length=10,
            description="RTSP stream URL (rtsp:// or rtsps://)",
            examples=["rtsp://admin:pass@192.168.1.100:554/stream"]
        )
    ]
    
    hw_accel_enabled: Annotated[
        bool,
        Field(
            default=True,
            description="Enable hardware acceleration if GPU available"
        )
    ]
    
    ffmpeg_params: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Custom FFmpeg parameters (empty uses service defaults)"
        )
    ]
    
    auto_start: Annotated[
        bool,
        Field(
            default=True,
            description="Automatically start stream when configured or on application restart"
        )
    ]
    
    created_at: Annotated[
        str,
        Field(
            default_factory=lambda: datetime.now(timezone.utc).isoformat(),
            description="ISO 8601 timestamp of stream creation"
        )
    ]
    
    order: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Display order in UI (0-based)"
        )
    ]
    
    status: Annotated[
        Literal["running", "stopped"],
        Field(
            default="stopped",
            description="Current stream processing status"
        )
    ]
    
    @model_validator(mode="after")
    def validate_rtsp_url_format(self) -> Stream:
        """Validate RTSP URL has correct protocol prefix.
        
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If URL doesn't start with rtsp:// or rtsps://
        """
        if not self.rtsp_url.startswith(("rtsp://", "rtsps://")):
            raise ValueError("RTSP URL must start with rtsp:// or rtsps://")
        return self


# ============================================================================
# Stream Creation Model
# ============================================================================

class NewStream(BaseModel):
    """Model for creating new streams.
    
    Excludes auto-generated fields (id, created_at, order, status).
    All fields required except hw_accel_enabled, ffmpeg_params, target_fps, and auto_start.
    """
    
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Human-readable stream name",
            examples=["Front Door Camera", "Parking Lot"]
        )
    ]
    
    rtsp_url: Annotated[
        str,
        Field(
            min_length=10,
            description="RTSP stream URL (rtsp:// or rtsps://)",
            examples=["rtsp://admin:pass@192.168.1.100:554/stream"]
        )
    ]
    
    hw_accel_enabled: Annotated[
        bool,
        Field(
            default=True,
            description="Enable hardware acceleration if GPU available"
        )
    ]
    
    ffmpeg_params: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Custom FFmpeg parameters (empty uses service defaults)"
        )
    ]
    
    auto_start: Annotated[
        bool,
        Field(
            default=True,
            description="Automatically start stream when configured or on application restart"
        )
    ]
    
    @model_validator(mode="after")
    def validate_rtsp_url_format(self) -> NewStream:
        """Validate RTSP URL has correct protocol prefix.
        
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If URL doesn't start with rtsp:// or rtsps://
        """
        if not self.rtsp_url.startswith(("rtsp://", "rtsps://")):
            raise ValueError("RTSP URL must start with rtsp:// or rtsps://")
        return self


# ============================================================================
# Stream Update Model
# ============================================================================

class EditStream(BaseModel):
    """Model for partial stream updates.
    
    All fields optional to support PATCH semantics.
    Only provided fields will be updated.
    """
    
    name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=50,
            description="Human-readable stream name",
            examples=["Front Door Camera", "Parking Lot"]
        )
    ]
    
    rtsp_url: Annotated[
        str | None,
        Field(
            default=None,
            min_length=10,
            description="RTSP stream URL (rtsp:// or rtsps://)",
            examples=["rtsp://admin:pass@192.168.1.100:554/stream"]
        )
    ]
    
    status: Annotated[
        Literal["running", "stopped"] | None,
        Field(
            default=None,
            description="Current stream processing status"
        )
    ]
    
    hw_accel_enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="Enable hardware acceleration if GPU available"
        )
    ]
    
    ffmpeg_params: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Custom FFmpeg parameters (empty uses service defaults)"
        )
    ]
    
    auto_start: Annotated[
        bool | None,
        Field(
            default=None,
            description="Update auto-start setting"
        )
    ]
    
    @model_validator(mode="after")
    def validate_rtsp_url_format(self) -> EditStream:
        """Validate RTSP URL has correct protocol prefix (if provided).
        
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If URL provided and doesn't start with rtsp:// or rtsps://
        """
        if self.rtsp_url is not None and not self.rtsp_url.startswith(("rtsp://", "rtsps://")):
            raise ValueError("RTSP URL must start with rtsp:// or rtsps://")
        return self


# ============================================================================
# Stream Reordering Model
# ============================================================================

class ReorderRequest(BaseModel):
    """Model for reordering streams in the UI.
    
    Contains an ordered list of stream IDs representing the new display order.
    """
    
    order: Annotated[
        list[str],
        Field(
            min_length=1,
            description="Ordered list of stream IDs (UUIDs)",
            examples=[
                ["uuid-1", "uuid-2", "uuid-3"],
                ["550e8400-e29b-41d4-a716-446655440000"]
            ]
        )
    ]
    
    @model_validator(mode="after")
    def validate_no_duplicates(self) -> ReorderRequest:
        """Validate no duplicate stream IDs in order list.
        
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If order contains duplicate IDs
        """
        if len(self.order) != len(set(self.order)):
            raise ValueError("Order list contains duplicate stream IDs")
        return self