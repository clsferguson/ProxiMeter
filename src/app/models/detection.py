"""
Pydantic models for YOLO object detection feature.

This module defines data models for:
- YOLOConfig: Container startup configuration
- Detection: Single object detection result
- StreamDetectionConfig: Per-stream detection settings
- DetectionMetrics: Performance metrics
- CachedModel: Model cache metadata

Feature: 005-yolo-object-detection
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Constants
# ============================================================================

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane",
    "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird",
    "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat",
    "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut",
    "cake", "chair", "couch", "potted plant", "bed",
    "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven",
    "toaster", "sink", "refrigerator", "book", "clock",
    "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

SUPPORTED_YOLO_MODELS = [
    # YOLO11 series (latest, recommended)
    "yolo11n", "yolo11s", "yolo11m", "yolo11l", "yolo11x",
    # YOLOv9 series
    "yolov9t", "yolov9s", "yolov9m", "yolov9l",
    # YOLOv8 series
    "yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x",
    # YOLOv7 series
    "yolov7", "yolov7x",
    # YOLOv6 series
    "yolov6n", "yolov6s", "yolov6m", "yolov6l"
]

SUPPORTED_IMAGE_SIZES = [320, 416, 512, 640, 1280]


# ============================================================================
# Pydantic Models
# ============================================================================

class YOLOConfig(BaseModel):
    """YOLO model configuration from environment variables."""

    model_name: str = Field(
        default="yolo11n",
        description="YOLO model variant",
        pattern="^(yolo11n|yolo11s|yolo11m|yolo11l|yolo11x|yolov9t|yolov9s|yolov9m|yolov9l|yolov8n|yolov8s|yolov8m|yolov8l|yolov8x|yolov7|yolov7x|yolov6n|yolov6s|yolov6m|yolov6l)$"
    )

    image_size: int = Field(
        default=640,
        description="Square input size for YOLO inference (pixels)",
        ge=320,
        le=1280
    )

    backend: Literal["nvidia", "amd", "intel", "none"] = Field(
        default="none",
        description="GPU backend detected/configured"
    )

    model_path: str = Field(
        description="Absolute path to cached ONNX model file",
        examples=["/app/models/yolo11n_640.onnx"]
    )

    class Config:
        frozen = True  # Immutable after initialization


class Detection(BaseModel):
    """Single object detection result."""

    class_id: int = Field(
        description="COCO class ID (0-79)",
        ge=0,
        lt=80
    )

    class_name: str = Field(
        description="Human-readable COCO class name",
        examples=["person"]
    )

    confidence: float = Field(
        description="Detection confidence score",
        ge=0.0,
        le=1.0
    )

    bbox: tuple[int, int, int, int] = Field(
        description="Bounding box in original frame coordinates (x1, y1, x2, y2)",
        examples=[(100, 150, 300, 450)]
    )

    class Config:
        frozen = True


class StreamDetectionConfig(BaseModel):
    """Per-stream object detection configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable/disable object detection for this stream"
    )

    enabled_labels: List[str] = Field(
        default_factory=lambda: ["person"],
        description="COCO class names to detect and display",
        min_items=0,
        max_items=80
    )

    min_confidence: float = Field(
        default=0.7,
        description="Minimum confidence threshold for displaying detections",
        ge=0.0,
        le=1.0,
        multiple_of=0.01
    )

    class Config:
        validate_assignment = True  # Validate on updates


class DetectionMetrics(BaseModel):
    """Detection pipeline performance metrics."""

    stream_id: str = Field(
        description="Stream identifier"
    )

    inference_time_ms: float = Field(
        description="YOLO inference latency (milliseconds)",
        ge=0
    )

    detections_count: int = Field(
        description="Number of detections in current frame (after filtering)",
        ge=0
    )

    frames_processed: int = Field(
        description="Total frames successfully processed with detection",
        ge=0
    )

    frames_skipped: int = Field(
        description="Frames skipped due to slow inference or errors",
        ge=0
    )

    preprocessing_time_ms: Optional[float] = Field(
        default=None,
        description="Frame preprocessing time (milliseconds)",
        ge=0
    )

    rendering_time_ms: Optional[float] = Field(
        default=None,
        description="Bounding box rendering time (milliseconds)",
        ge=0
    )

    total_pipeline_time_ms: Optional[float] = Field(
        default=None,
        description="End-to-end detection pipeline time (milliseconds)",
        ge=0
    )


class CachedModel(BaseModel):
    """Metadata for cached YOLO model."""

    model_name: str = Field(
        description="YOLO model variant name",
        examples=["yolo11n_640"]
    )

    file_path: str = Field(
        description="Absolute path to ONNX model file",
        examples=["/app/models/yolo11n_640.onnx"]
    )

    file_size_bytes: int = Field(
        description="Model file size in bytes",
        ge=0,
        examples=[6291456]
    )

    download_date: datetime = Field(
        description="Timestamp when model was downloaded/created"
    )

    is_active: bool = Field(
        description="Whether this model is currently loaded in ONNX Runtime",
        default=False
    )

    checksum: Optional[str] = Field(
        default=None,
        description="SHA256 checksum for integrity verification",
        examples=["abc123..."]
    )
