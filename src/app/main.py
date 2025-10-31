"""FastAPI application entry point for ProxiMeter.

ProxiMeter: GPU-accelerated RTSP stream processing with FFmpeg and REST APIs.

Architecture:
    - FastAPI async web framework
    - FFmpeg subprocesses for GPU-accelerated decoding
    - Singleton StreamsService for FFmpeg process management
    - React frontend SPA

Key Features:
    - RTSP stream ingestion with GPU acceleration
    - Real-time MJPEG streaming (5fps cap)
    - JPEG snapshot capture
    - Auto-start streams on boot
    - Graceful shutdown

Constitution Compliance:
    - GPU-only operation (no CPU fallback)
    - FFmpeg for ALL stream processing
    - 5fps streaming cap enforced
    - Full resolution preservation
    - No video storage (live frames only)

Critical Design Decisions:
    1. Singleton StreamsService: ALL requests use SAME instance with SAME
       active_processes dict. This was the root cause of "Stream not found"
       errors - each request was creating new service with empty dict.
    
    2. Container Module: Breaks circular import between main.py and api/streams.py
       by storing singleton in neutral module.
    
    3. Lifespan Context: Modern FastAPI pattern replacing @app.on_event.

Logging Strategy:
    INFO  - Application lifecycle, stream operations, config
    DEBUG - Internal state, diagnostics, detailed operations
    WARN  - Recoverable issues, missing GPU, auto-start failures
    ERROR - Unrecoverable errors with stack traces

Author: ProxiMeter Development Team
Version: 1.0.0
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import health, streams, zones, detection
from .api.errors import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from .logging_config import setup_logging
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_id import RequestIDMiddleware
from .services.streams_service import StreamsService
from .services import container

logger = logging.getLogger(__name__)

# Setup logging before anything else
setup_logging()

# ============================================================================
# Application Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup, running, shutdown.
    
    Startup Phase:
        1. Create singleton StreamsService
        2. Validate GPU backend
        3. Auto-start configured streams
    
    Shutdown Phase:
        1. Stop all running FFmpeg processes gracefully
        2. Wait for termination
    
    Why Singleton?
        Without singleton, each API request creates NEW StreamsService with
        EMPTY active_processes dict, causing "Stream not found" errors.
    
    Yields:
        Control to FastAPI during runtime
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    
    logger.info("=" * 80)
    logger.info("ProxiMeter starting...")
    logger.info("=" * 80)

    try:
        # Initialize YOLO model configuration
        from .models.detection import YOLOConfig
        from pathlib import Path

        yolo_model = os.getenv("YOLO_MODEL", "yolo11n")
        yolo_size = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
        gpu_backend_env = os.getenv("GPU_BACKEND_DETECTED", "none")
        model_path = f"/app/models/{yolo_model}_{yolo_size}.onnx"

        yolo_config = YOLOConfig(
            model_name=yolo_model,
            image_size=yolo_size,
            backend=gpu_backend_env,
            model_path=model_path
        )
        detection.set_yolo_config(yolo_config)
        logger.info(f"YOLO config: {yolo_model} ({yolo_size}x{yolo_size}), backend={gpu_backend_env}")

        # Initialize ONNX Runtime session if model exists
        if Path(model_path).exists():
            from .services.yolo import create_onnx_session
            try:
                onnx_session = create_onnx_session(model_path, gpu_backend_env, fail_fast=False)
                detection.set_onnx_session(onnx_session)
                logger.info(f"ONNX Runtime session initialized: {model_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize ONNX session: {e}")
                logger.warning("Detection features will be unavailable")
        else:
            logger.warning(f"YOLO model not found at {model_path}")
            logger.warning("Run container startup to download model via entrypoint.sh")

        # Initialize singleton
        container.streams_service = StreamsService()
        gpu_backend = container.streams_service.gpu_backend

        if gpu_backend == "none":
            logger.warning("No GPU detected - streams will fail to start")
            logger.warning("Requires NVIDIA/AMD/Intel GPU with drivers")
        else:
            logger.info(f"GPU backend: {gpu_backend}")

        # Auto-start streams
        await container.streams_service.start_all_streams()
        
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        logger.warning("Starting without streams support")
    
    logger.info("API documentation: /docs and /redoc")
    logger.info("=" * 80)
    logger.info("ProxiMeter ready")
    logger.info("=" * 80)
    
    # ========================================================================
    # RUNNING
    # ========================================================================
    
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    
    logger.info("=" * 80)
    logger.info("ProxiMeter shutting down...")
    logger.info("=" * 80)
    
    if container.streams_service is None:
        logger.warning("StreamsService was None during shutdown")
    else:
        try:
            streams_list = await container.streams_service.list_streams()
            running = [s for s in streams_list if s.get("status") == "running"]
            
            if not running:
                logger.info("No running streams to stop")
            else:
                logger.info(f"Stopping {len(running)} stream(s)...")
                
                # Stop all concurrently
                stop_tasks = [
                    container.streams_service.stop_stream(s["id"]) 
                    for s in running
                ]
                
                results = await asyncio.gather(*stop_tasks, return_exceptions=True)
                
                # Count successes/failures
                errors = [r for r in results if isinstance(r, Exception)]
                successful = len(results) - len(errors)
                
                if errors:
                    logger.error(f"Failed to stop {len(errors)}/{len(results)} stream(s)")
                    for idx, error in enumerate(errors, 1):
                        logger.error(f"  Stream {idx}: {error}")
                
                if successful > 0:
                    logger.info(f"Stopped {successful} stream(s)")
                
        except Exception as e:
            logger.error(f"Shutdown error: {e}", exc_info=True)
    
    logger.info("=" * 80)
    logger.info("ProxiMeter shutdown complete")
    logger.info("=" * 80)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="ProxiMeter",
    description=(
        "GPU-accelerated RTSP stream management API.\n\n"
        "Features:\n"
        "- GPU-accelerated FFmpeg processing\n"
        "- Real-time MJPEG streaming (5fps)\n"
        "- Snapshot capture\n"
        "- Detection zones (YOLO)\n"
        "- Auto-start on boot"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ============================================================================
# Exception Handlers
# ============================================================================

app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(Exception, general_exception_handler)

# ============================================================================
# Middleware (reverse order execution)
# ============================================================================

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_second=5.0, burst=10)

# ============================================================================
# API Routers
# ============================================================================

app.include_router(health.router, tags=["health"])
app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
app.include_router(zones.router, prefix="/api", tags=["zones"])
app.include_router(detection.router, tags=["detection"])

# ============================================================================
# Static Files (React Frontend)
# ============================================================================

STATIC_DIR = os.getenv("STATIC_ROOT", "/app/src/app/static/frontend")

if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
    logger.info(f"Frontend: {STATIC_DIR}")
else:
    logger.warning(f"Frontend not found: {STATIC_DIR}")
    logger.info("API endpoints still available at /api/*")

# ============================================================================
# Configuration Summary
# ============================================================================

env = os.getenv("ENV", "development")
log_level = os.getenv("LOG_LEVEL", "INFO")
app_port = os.getenv("APP_PORT", "8000")

logger.info(f"Environment: {env}")
logger.info(f"Log level: {log_level}")
logger.info(f"Port: {app_port}")

logger.debug(f"Config: ENV={env}, LOG_LEVEL={log_level}, PORT={app_port}, STATIC={STATIC_DIR}")