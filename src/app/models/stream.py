"""Stream domain models and Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Type Aliases
# ============================================================================

StreamStatus = Literal["running", "stopped", "error"]


# ============================================================================
# Stream Models
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
    
    target_fps: Annotated[
        int,
        Field(
            default=5,
            ge=1,
            le=30,
            description="Target frames per second for processing"
        )
    ]
    
    created_at: Annotated[
        str,
        Field(
            default_factory=lambda: datetime.now(timezone.utc).isoformat(),
            description="ISO 8601 creation timestamp (UTC)"
        )
    ]
    
    order: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Display order (0-based index)"
        )
    ]
    
    status: Annotated[
        StreamStatus,
        Field(
            default="stopped",
            description="Current stream status"
        )
    ]
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim and validate name."""
        v = v.strip()
        if not v:
            raise ValueError("Stream name cannot be empty")
        if len(v) > 50:
            raise ValueError("Stream name must be at most 50 characters")
        return v
    
    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str) -> str:
        """Validate RTSP URL format."""
        v = v.strip()
        
        if not v.lower().startswith(("rtsp://", "rtsps://")):
            raise ValueError("RTSP URL must start with rtsp:// or rtsps://")
        
        if len(v) < 10:  # rtsp://x/y minimum
            raise ValueError("RTSP URL must include host and path")
        
        return v
    
    @field_validator("ffmpeg_params")
    @classmethod
    def validate_ffmpeg_params(cls, v: list[str]) -> list[str]:
        """Validate FFmpeg params for security (shell injection prevention)."""
        if not v:
            return v
        
        # Shell metacharacters that could enable command injection
        forbidden_chars = {";", "&", "|", ">", "<", "`", "$", "\n", "\r", "\\"}
        
        for param in v:
            if not isinstance(param, str):
                raise ValueError(f"FFmpeg param must be string, got {type(param)}")
            
            # Check for shell metacharacters
            if any(char in param for char in forbidden_chars):
                raise ValueError(
                    f"FFmpeg param '{param}' contains forbidden shell characters"
                )
            
            # Basic whitelist: allow flags (-xxx), numbers, and alphanumeric values
            # This catches most legitimate FFmpeg params while blocking suspicious input
            if param.startswith("-"):
                # Allow flags like -threads, -rtsp_transport
                continue
            elif param.replace(".", "").replace(":", "").replace("/", "").isalnum():
                # Allow numeric and alphanumeric values (paths, numbers, etc)
                continue
            else:
                # Be permissive for edge cases but log warning
                # (e.g., "tcp", "warning", etc)
                if not param.replace("_", "").isalnum():
                    raise ValueError(
                        f"Suspicious FFmpeg param '{param}' - contains unexpected characters"
                    )
        
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Front Door Camera",
                "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
                "hw_accel_enabled": True,
                "ffmpeg_params": ["-rtsp_transport", "tcp"],
                "target_fps": 5,
                "created_at": "2025-10-24T19:00:00Z",
                "order": 0,
                "status": "stopped"
            }
        }
    )


class NewStream(BaseModel):
    """Schema for creating a new stream.
    
    Used in POST /api/streams endpoint.
    """
    
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Human-readable stream name"
        )
    ]
    
    rtsp_url: Annotated[
        str,
        Field(
            min_length=10,
            description="RTSP stream URL"
        )
    ]
    
    hw_accel_enabled: Annotated[
        bool,
        Field(
            default=True,
            description="Enable hardware acceleration"
        )
    ]
    
    ffmpeg_params: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Custom FFmpeg params (null uses service defaults)"
        )
    ] = None
    
    target_fps: Annotated[
        int,
        Field(
            default=5,
            ge=1,
            le=30,
            description="Target FPS"
        )
    ]
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim and validate name."""
        return Stream.validate_name(v)
    
    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str) -> str:
        """Validate RTSP URL format."""
        return Stream.validate_rtsp_url(v)
    
    @field_validator("ffmpeg_params")
    @classmethod
    def validate_ffmpeg_params(cls, v: list[str] | None) -> list[str] | None:
        """Validate FFmpeg params if provided."""
        if v is None:
            return None
        return Stream.validate_ffmpeg_params(v)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Front Door Camera",
                "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
                "hw_accel_enabled": True,
                "ffmpeg_params": None,
                "target_fps": 5
            }
        }
    )


class EditStream(BaseModel):
    """Schema for partial stream updates.
    
    Used in PATCH /api/streams/{id} endpoint.
    All fields are optional to support partial updates.
    """
    
    name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=50,
            description="New stream name (optional)"
        )
    ] = None
    
    rtsp_url: Annotated[
        str | None,
        Field(
            default=None,
            min_length=10,
            description="New RTSP URL (optional)"
        )
    ] = None
    
    hw_accel_enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="New hardware acceleration setting (optional)"
        )
    ] = None
    
    ffmpeg_params: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="New FFmpeg params (optional)"
        )
    ] = None
    
    target_fps: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            le=30,
            description="New target FPS (optional)"
        )
    ] = None
    
    status: Annotated[
        StreamStatus | None,
        Field(
            default=None,
            description="New status (optional, typically set by system)"
        )
    ] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Trim and validate name if provided."""
        if v is None:
            return None
        return Stream.validate_name(v)
    
    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str | None) -> str | None:
        """Validate RTSP URL format if provided."""
        if v is None:
            return None
        return Stream.validate_rtsp_url(v)
    
    @field_validator("ffmpeg_params")
    @classmethod
    def validate_ffmpeg_params(cls, v: list[str] | None) -> list[str] | None:
        """Validate FFmpeg params if provided."""
        if v is None:
            return None
        return Stream.validate_ffmpeg_params(v)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Front Door Camera",
                "target_fps": 10
            }
        }
    )


# ============================================================================
# Response Models
# ============================================================================

class StreamList(BaseModel):
    """Response model for list of streams."""
    
    streams: Annotated[
        list[Stream],
        Field(description="List of streams sorted by order")
    ]
    
    count: Annotated[
        int,
        Field(description="Total number of streams")
    ]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "streams": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Front Door",
                        "rtsp_url": "rtsp://192.168.1.100/stream",
                        "hw_accel_enabled": True,
                        "ffmpeg_params": [],
                        "target_fps": 5,
                        "created_at": "2025-10-24T19:00:00Z",
                        "order": 0,
                        "status": "stopped"
                    }
                ],
                "count": 1
            }
        }
    )


class ReorderRequest(BaseModel):
    """Request model for reordering streams."""
    
    order: Annotated[
        list[str],
        Field(
            min_length=1,
            description="List of stream IDs in desired order"
        )
    ]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "223e4567-e89b-12d3-a456-426614174000"
                ]
            }
        }
    )
