"""
Detection API endpoints for YOLO object detection.

Endpoints:
- GET /api/yolo/config - Get YOLO model configuration
- GET /api/models - List cached models
- DELETE /api/models/{model_name} - Delete cached model
- GET /api/streams/{stream_id}/detection - Get stream detection config
- PUT /api/streams/{stream_id}/detection - Update stream detection config

Feature: 005-yolo-object-detection
"""

from fastapi import APIRouter, HTTPException, status
from app.models.detection import YOLOConfig, CachedModel, StreamDetectionConfig
from app.services.yolo import list_cached_models, delete_cached_model
from app.config_io import load_streams, save_streams, atomic_config_update
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["detection"])

# Global YOLO config and ONNX session (loaded at startup)
_yolo_config: YOLOConfig | None = None
_onnx_session = None


def set_yolo_config(config: YOLOConfig):
    """Set global YOLO configuration (called from startup)."""
    global _yolo_config
    _yolo_config = config


def set_onnx_session(session):
    """Set global ONNX Runtime session (called from startup)."""
    global _onnx_session
    _onnx_session = session


def get_onnx_session():
    """Get global ONNX Runtime session."""
    return _onnx_session


def get_yolo_config_singleton() -> YOLOConfig | None:
    """Get global YOLO configuration singleton."""
    return _yolo_config


@router.get("/yolo/config", response_model=YOLOConfig)
async def get_yolo_config():
    """
    Get current YOLO model configuration.

    Returns configuration loaded at container startup from environment variables.
    """
    if _yolo_config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model not initialized"
        )
    return _yolo_config


@router.get("/models")
async def get_cached_models():
    """
    List all cached YOLO models.

    Returns metadata for all .onnx files in /app/models directory.
    """
    try:
        models = list_cached_models()

        # Determine active model
        active_model = None
        if _yolo_config:
            active_model = Path(_yolo_config.model_path).stem

        # Mark active model
        for model in models:
            model["is_active"] = (model["model_name"] == active_model)

        return {
            "models": models,
            "active_model": active_model
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """
    Delete a cached YOLO model.

    Cannot delete the currently active model (returns 409 Conflict).
    """
    # Check if this is the active model
    if _yolo_config and Path(_yolo_config.model_path).stem == model_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete active model: {model_name}"
        )

    try:
        freed_bytes = delete_cached_model(model_name)
        return {
            "success": True,
            "message": f"Deleted model {model_name}.onnx",
            "freed_bytes": freed_bytes
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {model_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}"
        )


@router.get("/streams/{stream_id}/detection", response_model=StreamDetectionConfig)
async def get_stream_detection_config(stream_id: str):
    """
    Get detection configuration for a specific stream.

    Returns the current detection settings (enabled, labels, confidence threshold).
    """
    try:
        config = load_streams()
        streams = config.get("streams", [])

        for stream in streams:
            if stream.get("id") == stream_id:
                detection_config = stream.get("detection", {})
                return StreamDetectionConfig(**detection_config)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream not found: {stream_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get detection config: {str(e)}"
        )


@router.put("/streams/{stream_id}/detection")
async def update_stream_detection_config(stream_id: str, detection_config: StreamDetectionConfig):
    """
    Update detection configuration for a specific stream.

    Changes apply immediately to live streams without restart.
    Validates enabled_labels against COCO_CLASSES.
    """
    from app.models.detection import COCO_CLASSES
    from app.services import container

    try:
        # Validate enabled_labels against COCO_CLASSES
        invalid_labels = [label for label in detection_config.enabled_labels if label not in COCO_CLASSES]
        if invalid_labels:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Invalid COCO class labels",
                    "invalid_labels": invalid_labels,
                    "valid_labels": COCO_CLASSES
                }
            )

        # Atomic read-modify-write to prevent race conditions
        stream_found = False
        with atomic_config_update() as config:
            streams = config.get("streams", [])

            for stream in streams:
                if stream.get("id") == stream_id:
                    stream["detection"] = detection_config.model_dump()
                    stream_found = True
                    break

            if not stream_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stream not found: {stream_id}"
                )

        # Apply changes immediately to running stream (if active)
        applied_immediately = False
        if container.streams_service:
            # Use lock to prevent race conditions when updating active_processes
            async with container.streams_service.active_processes_lock:
                active_processes = container.streams_service.active_processes
                if stream_id in active_processes:
                    active_processes[stream_id]["detection_config"] = detection_config.model_dump()
                    applied_immediately = True
                    logger.info(f"Detection config updated live for stream {stream_id}")

        return {
            "success": True,
            "message": f"Detection config updated for stream {stream_id}",
            "applied_immediately": applied_immediately
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update detection config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update detection config: {str(e)}"
        )
