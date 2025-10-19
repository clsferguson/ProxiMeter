"""Stream domain model and Pydantic schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime
import uuid


class Stream(BaseModel):
    """Complete stream model with all fields."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=50)
    rtsp_url: str = Field(..., min_length=1)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    order: int = Field(default=0, ge=0)
    status: Literal["Active", "Inactive"] = Field(default="Active")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim and validate name."""
        v = v.strip()
        if not v or len(v) > 50:
            raise ValueError("Name must be 1-50 characters after trimming")
        return v
    
    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str) -> str:
        """Validate RTSP URL format."""
        v = v.strip()
        if not v.startswith("rtsp://"):
            raise ValueError("RTSP URL must start with rtsp://")
        # Basic validation - detailed validation in service layer
        if len(v) < 10:  # rtsp://x/y minimum
            raise ValueError("RTSP URL must include host")
        return v


class NewStream(BaseModel):
    """Schema for creating a new stream."""
    
    name: str = Field(..., min_length=1, max_length=50)
    rtsp_url: str = Field(..., min_length=1)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim and validate name."""
        v = v.strip()
        if not v or len(v) > 50:
            raise ValueError("Name must be 1-50 characters after trimming")
        return v
    
    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str) -> str:
        """Validate RTSP URL format."""
        v = v.strip()
        if not v.startswith("rtsp://"):
            raise ValueError("RTSP URL must start with rtsp://")
        if len(v) < 10:
            raise ValueError("RTSP URL must include host")
        return v


class EditStream(BaseModel):
    """Schema for editing an existing stream (partial updates)."""
    
    name: str | None = Field(None, min_length=1, max_length=50)
    rtsp_url: str | None = Field(None, min_length=1)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Trim and validate name if provided."""
        if v is not None:
            v = v.strip()
            if not v or len(v) > 50:
                raise ValueError("Name must be 1-50 characters after trimming")
        return v
    
    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str | None) -> str | None:
        """Validate RTSP URL format if provided."""
        if v is not None:
            v = v.strip()
            if not v.startswith("rtsp://"):
                raise ValueError("RTSP URL must start with rtsp://")
            if len(v) < 10:
                raise ValueError("RTSP URL must include host")
        return v
