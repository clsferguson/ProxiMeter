"""Zone models for detection regions within video streams."""
from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Zone Models
# ============================================================================

class ZoneCoordinates(BaseModel):
    """Normalized polygon coordinates for zone detection.
    
    Coordinates are normalized to 0.0-1.0 range relative to video frame dimensions.
    This ensures zones work across different resolutions.
    """
    
    x: Annotated[float, Field(ge=0.0, le=1.0, description="Normalized X coordinate (0.0-1.0)")]
    y: Annotated[float, Field(ge=0.0, le=1.0, description="Normalized Y coordinate (0.0-1.0)")]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"x": 0.5, "y": 0.5}
        }
    )


class NewZone(BaseModel):
    """Model for creating a new detection zone.
    
    Zones define regions of interest within a video stream where
    object detection should be performed.
    """
    
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Human-readable zone name",
            examples=["Entry Zone", "Parking Area", "Restricted Zone"]
        )
    ]
    
    coordinates: Annotated[
        list[list[float]],
        Field(
            min_length=3,
            description="Polygon coordinates as [[x1, y1], [x2, y2], ...] where values are 0.0-1.0",
            examples=[[[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]]]
        )
    ]
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: list[list[float]]) -> list[list[float]]:
        """Validate polygon coordinates structure and values.
        
        Ensures:
        - At least 3 points (minimum for a polygon)
        - Each point has exactly 2 coordinates [x, y]
        - All coordinates are in range 0.0-1.0
        """
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 points")
        
        for i, point in enumerate(v):
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(f"Point {i} must be a list of [x, y]")
            
            x, y = point
            
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError(f"Point {i} coordinates must be numbers")
            
            if not (0.0 <= x <= 1.0):
                raise ValueError(f"Point {i} x-coordinate must be between 0.0 and 1.0 (got {x})")
            
            if not (0.0 <= y <= 1.0):
                raise ValueError(f"Point {i} y-coordinate must be between 0.0 and 1.0 (got {y})")
        
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Entry Zone",
                "coordinates": [
                    [0.1, 0.1],
                    [0.9, 0.1],
                    [0.9, 0.5],
                    [0.1, 0.5]
                ]
            }
        }
    )


class EditZone(BaseModel):
    """Model for partial zone updates.
    
    All fields are optional to support partial updates.
    Only provided fields will be updated.
    """
    
    name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=50,
            description="New zone name (optional)"
        )
    ] = None
    
    coordinates: Annotated[
        list[list[float]] | None,
        Field(
            default=None,
            min_length=3,
            description="New polygon coordinates (optional)"
        )
    ] = None
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: list[list[float]] | None) -> list[list[float]] | None:
        """Validate coordinates if provided."""
        if v is None:
            return v
        
        # Reuse validation from NewZone
        return NewZone.validate_coordinates(v)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Entry Zone"
            }
        }
    )


class Zone(BaseModel):
    """Complete zone model with all fields.
    
    Represents a fully-defined detection zone within a stream.
    """
    
    id: Annotated[
        str,
        Field(
            default_factory=lambda: str(uuid.uuid4()),
            description="Unique zone identifier (UUID)"
        )
    ]
    
    stream_id: Annotated[
        str,
        Field(description="Parent stream UUID")
    ]
    
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Human-readable zone name"
        )
    ]
    
    coordinates: Annotated[
        list[list[float]],
        Field(
            min_length=3,
            description="Polygon coordinates [[x1, y1], [x2, y2], ...] (normalized 0.0-1.0)"
        )
    ]
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: list[list[float]]) -> list[list[float]]:
        """Validate coordinates."""
        return NewZone.validate_coordinates(v)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "stream_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Entry Zone",
                "coordinates": [
                    [0.1, 0.1],
                    [0.9, 0.1],
                    [0.9, 0.5],
                    [0.1, 0.5]
                ]
            }
        }
    )


# ============================================================================
# Response Models
# ============================================================================

class ZoneList(BaseModel):
    """Response model for list of zones."""
    
    zones: Annotated[
        list[Zone],
        Field(description="List of zones for the stream")
    ]
    
    count: Annotated[
        int,
        Field(description="Total number of zones")
    ]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "zones": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "stream_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Entry Zone",
                        "coordinates": [[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]]
                    }
                ],
                "count": 1
            }
        }
    )
