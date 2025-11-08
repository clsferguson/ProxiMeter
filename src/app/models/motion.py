"""
Pydantic models for motion-based detection with object tracking.

This module defines data models for:
- MotionRegion: Detected motion area from background subtraction
- ObjectState: Lifecycle states for tracked objects
- TrackedObject: Object with Kalman filter state and history
- MotionDetectionMetrics: Per-stream performance metrics

Feature: 006-motion-tracking
"""

from enum import Enum
from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class ObjectState(str, Enum):
    """Tracked object lifecycle states."""
    TENTATIVE = "tentative"       # Initial detection, not yet confirmed
    ACTIVE = "active"              # Confirmed and actively moving
    STATIONARY = "stationary"      # Stopped moving (50 frame threshold)
    LOST = "lost"                  # No detection match (prediction only)


# ============================================================================
# Pydantic Models
# ============================================================================

class MotionRegion(BaseModel):
    """Detected motion region in frame coordinates."""

    bounding_box: Tuple[int, int, int, int] = Field(
        ...,
        description="Bounding box (x, y, width, height) in frame coordinates"
    )

    area: int = Field(
        ...,
        ge=0,
        description="Area in pixels (width * height)"
    )

    timestamp: float = Field(
        ...,
        description="Frame timestamp (seconds since stream start)"
    )

    merged_count: int = Field(
        default=1,
        ge=1,
        description="Number of contours merged into this region"
    )

    @property
    def x(self) -> int:
        """X coordinate of top-left corner."""
        return self.bounding_box[0]

    @property
    def y(self) -> int:
        """Y coordinate of top-left corner."""
        return self.bounding_box[1]

    @property
    def width(self) -> int:
        """Width of bounding box."""
        return self.bounding_box[2]

    @property
    def height(self) -> int:
        """Height of bounding box."""
        return self.bounding_box[3]

    @property
    def center(self) -> Tuple[float, float]:
        """Returns (cx, cy) center point."""
        return (self.x + self.width / 2, self.y + self.height / 2)


class TrackedObject(BaseModel):
    """Tracked object with Kalman filter state."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique tracking ID (persists across frames)"
    )

    class_name: str = Field(
        ...,
        description="YOLO class label (e.g., 'person', 'car')"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Latest detection confidence score"
    )

    bounding_box: Tuple[int, int, int, int] = Field(
        ...,
        description="Current bounding box (x, y, width, height)"
    )

    bounding_box_history: List[Tuple[int, int, int, int]] = Field(
        default_factory=list,
        description="Last 50 bounding boxes for stationary detection"
    )

    velocity: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="Estimated velocity (vx, vy) in pixels per frame"
    )

    state: ObjectState = Field(
        default=ObjectState.TENTATIVE,
        description="Current object state in lifecycle"
    )

    last_seen_frame: int = Field(
        ...,
        description="Frame number when last matched with detection"
    )

    frames_since_detection: int = Field(
        default=0,
        ge=0,
        description="Frames since last detection match (for timeout)"
    )

    frames_stationary: int = Field(
        default=0,
        ge=0,
        description="Consecutive frames with minimal movement"
    )

    detection_interval: int = Field(
        default=1,
        ge=1,
        description="Run detection every N frames (1=every frame, 50=stationary)"
    )

    hits: int = Field(
        default=1,
        ge=1,
        description="Total successful detection matches (for confirmation)"
    )

    age: int = Field(
        default=1,
        ge=1,
        description="Total frames since track creation"
    )

    @field_validator('bounding_box_history')
    @classmethod
    def limit_history_length(cls, v):
        """Keep only last 50 bounding boxes."""
        return v[-50:] if len(v) > 50 else v

    @property
    def center(self) -> Tuple[float, float]:
        """Returns (cx, cy) center point."""
        x, y, w, h = self.bounding_box
        return (x + w / 2, y + h / 2)

    @property
    def is_stationary(self) -> bool:
        """Check if object meets stationary threshold."""
        return self.frames_stationary >= 50

    def should_run_detection(self, current_frame: int) -> bool:
        """Check if detection should run on current frame."""
        return (current_frame - self.last_seen_frame) % self.detection_interval == 0

    def update_state(self):
        """Update state based on movement and detection history."""
        import logging
        logger = logging.getLogger(__name__)

        # Store previous state for logging
        previous_state = self.state

        if self.frames_since_detection > 30:
            self.state = ObjectState.LOST
        elif self.frames_stationary >= 50:
            self.state = ObjectState.STATIONARY
            self.detection_interval = 50
        elif self.hits >= 3:
            self.state = ObjectState.ACTIVE
            self.detection_interval = 1
        else:
            self.state = ObjectState.TENTATIVE

        # Log state transitions (T079: INFO-level structured logging)
        if previous_state != self.state:
            logger.info(
                f"Object state transition: id={self.id.hex[:8]}, "
                f"{previous_state.value} → {self.state.value}, "
                f"class={self.class_name}, hits={self.hits}, "
                f"frames_stationary={self.frames_stationary}, "
                f"frames_since_detection={self.frames_since_detection}"
            )


class MotionDetectionMetrics(BaseModel):
    """Per-stream motion detection metrics."""

    stream_id: str = Field(
        ...,
        description="Stream identifier"
    )

    motion_regions_count: int = Field(
        default=0,
        ge=0,
        description="Number of motion regions detected in current frame"
    )

    tracked_objects_count: int = Field(
        default=0,
        ge=0,
        description="Number of actively tracked objects (ACTIVE + TENTATIVE)"
    )

    stationary_objects_count: int = Field(
        default=0,
        ge=0,
        description="Number of stationary objects (reduced detection frequency)"
    )

    lost_objects_count: int = Field(
        default=0,
        ge=0,
        description="Number of lost objects (prediction only, no detection)"
    )

    gpu_utilization_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="GPU utilization percentage (if available)"
    )

    motion_detection_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="CPU time for motion detection (background subtraction + contours)"
    )

    yolo_inference_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="GPU time for YOLO inference on motion regions"
    )

    tracking_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="CPU time for Kalman filter tracking and matching"
    )

    total_frame_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total frame processing time (should be ≤200ms at 5 FPS)"
    )

    timestamp: float = Field(
        ...,
        description="Metrics timestamp (Unix seconds)"
    )
