"""Zone models for Pydantic validation."""
from pydantic import BaseModel, Field
from typing import List, Tuple
import uuid

class NewZone(BaseModel):
    """Model for creating a new zone."""
    name: str = Field(..., min_length=1, max_length=50, description="Zone name")
    coordinates: List[Tuple[int, int]] = Field(
        ..., 
        min_length=3, 
        description="Polygon coordinates (at least 3 points)"
    )

class EditZone(BaseModel):
    """Model for editing a zone."""
    name: str | None = Field(None, min_length=1, max_length=50)
    coordinates: List[Tuple[int, int]] | None = Field(None, min_length=3)

class Zone(BaseModel):
    """Complete zone model with all fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str
    name: str = Field(min_length=1, max_length=50)
    coordinates: List[Tuple[int, int]] = Field(min_length=3)
