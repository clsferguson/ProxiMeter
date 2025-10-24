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
    hw_accel_enabled: bool = Field(default=True)
    ffmpeg_params: list[str] = Field(default_factory=lambda: ["-hide_banner", "-loglevel", "warning", "-threads", "2", "-rtsp_transport", "tcp", "-timeout", "10000000"])
    target_fps: int = Field(default=5, ge=1, le=30)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    order: int = Field(default=0, ge=0)
    status: Literal["Active", "Inactive", "running", "stopped", "error"] = Field(default="stopped")
    
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
    
    @field_validator("ffmpeg_params")
    @classmethod
    def validate_ffmpeg_params(cls, v: list[str]) -> list[str]:
        """Validate FFmpeg params: no shell metachars, whitelist common flags."""
        forbidden = [";", "&", "|", ">", "<", "`", "$"]
        for param in v:
            if any(f in param for f in forbidden):
                raise ValueError(f"Invalid FFmpeg param: {param} contains shell metachars")
            # Whitelist: allow -flag value patterns
            if not (param.startswith("-") or param.isdigit() or param.replace(".", "").replace(":", "").isalnum()):
                raise ValueError(f"Suspicious FFmpeg param: {param}")
        return v


class NewStream(BaseModel):
    """Schema for creating a new stream."""
    
    name: str = Field(..., min_length=1, max_length=50)
    rtsp_url: str = Field(..., min_length=1)
    hw_accel_enabled: bool = Field(default=True)
    ffmpeg_params: list[str] | None = Field(None, description="Optional FFmpeg params; defaults applied if None")
    target_fps: int = Field(default=5, ge=1, le=30)
    
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
    
    @field_validator("ffmpeg_params")
    @classmethod
    def validate_ffmpeg_params(cls, v: list[str] | None) -> list[str] | None:
        """Validate FFmpeg params if provided."""
        if v is None:
            return None
        return Stream.validate_ffmpeg_params(v)


class EditStream(BaseModel):
    """Schema for editing an existing stream (partial updates)."""
    
    name: str | None = Field(None, min_length=1, max_length=50)
    rtsp_url: str | None = Field(None, min_length=1)
    hw_accel_enabled: bool | None = Field(None)
    ffmpeg_params: list[str] | None = Field(None)
    target_fps: int | None = Field(None, ge=1, le=30)
    status: Literal["Active", "Inactive", "running", "stopped", "error"] | None = None
    
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
    
    @field_validator("ffmpeg_params")
    @classmethod
    def validate_ffmpeg_params(cls, v: list[str] | None) -> list[str] | None:
        """Validate FFmpeg params if provided."""
        if v is None:
            return None
        return Stream.validate_ffmpeg_params(v)
