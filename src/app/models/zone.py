"""Zone models for detection regions within video streams.

Detection zones define polygonal areas of interest for person detection scoring.
Coordinates are normalized (0.0-1.0) to work across different video resolutions.

Polygon Format:
    [[x1, y1], [x2, y2], [x3, y3], ...]
    where x and y are normalized coordinates (0.0 = left/top, 1.0 = right/bottom)

Validation:
    - Minimum 3 points (triangle)
    - Each point must be [x, y] with values 0.0-1.0
    - Coordinates validated on creation and update

Constitution Compliance:
    - Normalized coordinates (resolution-independent)
    - Polygon-based zones for Shapely integration
    - Supports future YOLO + Shapely detection scoring
"""
from __future__ import annotations

import uuid
from pydantic import BaseModel, Field, field_validator, ConfigDict

# ============================================================================
# Validation Helpers
# ============================================================================

def validate_polygon_coordinates(coords: list[list[float]]) -> list[list[float]]:
    """Validate polygon coordinates structure and values.
    
    Ensures:
    - At least 3 points (minimum for polygon)
    - Each point is [x, y] with exactly 2 values
    - All coordinates in range 0.0-1.0 (normalized)
    
    Args:
        coords: List of [x, y] coordinate pairs
        
    Returns:
        Validated coordinates (unchanged)
        
    Raises:
        ValueError: If validation fails with descriptive message
    """
    if len(coords) < 3:
        raise ValueError("Polygon must have at least 3 points")
    
    for i, point in enumerate(coords):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"Point {i} must be [x, y]")
        
        x, y = point
        
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f"Point {i} coordinates must be numbers")
        
        if not (0.0 <= x <= 1.0):
            raise ValueError(f"Point {i} x must be 0.0-1.0 (got {x})")
        
        if not (0.0 <= y <= 1.0):
            raise ValueError(f"Point {i} y must be 0.0-1.0 (got {y})")
    
    return coords


# ============================================================================
# Zone Models
# ============================================================================

class NewZone(BaseModel):
    """Model for creating a new detection zone.
    
    Zones define regions where person detection scoring is performed.
    """
    
    name: str = Field(
        min_length=1,
        max_length=50,
        description="Zone name",
        examples=["Entry Zone", "Parking Area", "Restricted Zone"]
    )
    
    coordinates: list[list[float]] = Field(
        min_length=3,
        description="Polygon vertices [[x1, y1], [x2, y2], ...] (normalized 0.0-1.0)",
        examples=[[[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]]]
    )
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: list[list[float]]) -> list[list[float]]:
        """Validate polygon coordinates."""
        return validate_polygon_coordinates(v)
    
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
    """Model for partial zone updates (PATCH semantics).
    
    All fields optional - only provided fields are updated.
    """
    
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="New zone name"
    )
    
    coordinates: list[list[float]] | None = Field(
        default=None,
        min_length=3,
        description="New polygon coordinates"
    )
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: list[list[float]] | None) -> list[list[float]] | None:
        """Validate coordinates if provided."""
        if v is not None:
            return validate_polygon_coordinates(v)
        return v
    
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
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Zone UUID"
    )
    
    stream_id: str = Field(
        description="Parent stream UUID"
    )
    
    name: str = Field(
        min_length=1,
        max_length=50,
        description="Zone name"
    )
    
    coordinates: list[list[float]] = Field(
        min_length=3,
        description="Polygon vertices [[x1, y1], ...] (normalized 0.0-1.0)"
    )
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: list[list[float]]) -> list[list[float]]:
        """Validate polygon coordinates."""
        return validate_polygon_coordinates(v)
    
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
