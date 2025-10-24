"""Zone Pydantic models."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class Point(BaseModel):
    x: float = Field(..., ge=0, le=1, description="Normalized x (0-1)")
    y: float = Field(..., ge=0, le=1, description="Normalized y (0-1)")

class Zone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str
    name: str = Field(..., min_length=1, max_length=50)
    points: List[Point] = Field(..., min_items=3)
    enabled_metrics: List[str] = Field(default=["distance", "coordinates", "size"])
    target_point: Optional[Point] = None
    active: bool = Field(default=True)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class NewZone(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    points: List[Point] = Field(..., min_items=3)
    enabled_metrics: List[str] = Field(default=["distance", "coordinates", "size"])
    target_point: Optional[Point] = None

class EditZone(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    points: Optional[List[Point]] = Field(None, min_items=3)
    enabled_metrics: Optional[List[str]] = None
    target_point: Optional[Point] = None
    active: Optional[bool] = None
