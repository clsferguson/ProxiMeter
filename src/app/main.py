"""FastAPI application entry point for ProxiMeter RTSP Stream Management.

ProxiMeter is a GPU-accelerated RTSP stream processing application that uses
FFmpeg for video decoding and provides REST APIs for stream management, MJPEG
streaming, and snapshot capture.

Architecture:
    - FastAPI web framework with async/await
    - FFmpeg subprocesses for RTSP stream processing
    - GPU hardware acceleration (NVIDIA/AMD/Intel)
    - Singleton StreamsService for persistent FFmpeg process management
    - React frontend for web UI

Key Features:
    - RTSP stream ingestion with GPU-accelerated decoding
    - Real-time MJPEG streaming at 5 FPS
    - JPEG snapshot capture for dashboard thumbnails
    - Auto-start streams on application boot
    - Graceful shutdown of all FFmpeg processes

Constitution-compliant:
    - GPU-only operation (no CPU fallback)
    - FFmpeg for all stream processing
    - 5fps streaming cap
    - Full resolution preservation
    - No video storage (live frames only)

Module Structure:
    - main.py (this file): Application initialization and lifecycle
    - services/container.py: Singleton service holder (avoids circular imports)
    - services/streams_service.py: FFmpeg process management
    - api/streams.py: REST API endpoints for stream operations
    - api/health.py: Health check endpoints
    - api/zones.py: Detection zone management (future YOLO integration)

Critical Design Decisions:
    1. Singleton StreamsService: All API requests must use the SAME instance
       to access the SAME active_processes dict where FFmpeg processes live.
       This was the root cause of the original bug - each request was creating
       a new service with an empty dict.
    
    2. Container Module: Breaks circular import between main.py and api/streams.py
       by storing the singleton in a neutral third module.
    
    3. Lifespan Context Manager: Modern FastAPI pattern for startup/shutdown
       events, replacing deprecated @app.on_event decorators.

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

from .api import health, streams, zones
from .api.errors import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from .logging_config import setup_logging
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_id import RequestIDMiddleware
from .services.streams_service import StreamsService

# ============================================================================
# CRITICAL: Import Service Container (Avoids Circular Import)
# ============================================================================
# The container module holds the singleton StreamsService instance.
# This breaks the circular dependency:
#   - main.py imports container (no cycle)
#   - api/streams.py imports container (no cycle)
#   - container.py doesn't import main or api (no cycle)
from .services import container

logger = logging.getLogger(__name__)

# Setup logging configuration before anything else
setup_logging()


# ============================================================================
# Application Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.
    
    This replaces the deprecated @app.on_event("startup") and 
    @app.on_event("shutdown") decorators with a modern async context manager.
    
    Startup Phase:
        1. Creates singleton StreamsService instance
        2. Validates GPU backend availability
        3. Auto-starts streams with auto_start=True flag
        4. Logs initialization status
    
    Running Phase:
        - Yields control to FastAPI server
        - All requests use the singleton service via container
    
    Shutdown Phase:
        1. Lists all configured streams
        2. Gracefully stops all running FFmpeg processes
        3. Waits for all processes to terminate
        4. Logs shutdown status
    
    Why Singleton Service?
        Without a singleton, each API request creates a NEW StreamsService
        with an EMPTY active_processes dict. This causes "Stream not in 
        active_processes" errors because:
        - start_stream() adds process to dict in instance A
        - get_snapshot() looks for process in dict in instance B (empty!)
        - Process exists but can't be found
        
        The singleton ensures ALL requests see the SAME dict.
    
    Yields:
        None: Control is yielded to FastAPI during application runtime
    """
    # ========================================================================
    # STARTUP PHASE
    # ========================================================================
    
    logger.info("=" * 80)
    logger.info("🚀 ProxiMeter starting up...")
    logger.info("=" * 80)
    logger.info("📚 API documentation available at /docs")
    logger.info("📖 Alternative docs available at /redoc")
    
    # Initialize the singleton StreamsService instance
    # This instance persists for the entire application lifetime
    try:
        logger.info("🔧 Initializing StreamsService...")
        container.streams_service = StreamsService()
        
        # Log GPU backend detection
        gpu_backend = container.streams_service.gpu_backend
        if gpu_backend == "none":
            logger.warning("⚠️  No GPU detected! Streams will fail to start.")
            logger.warning("   This application requires NVIDIA/AMD/Intel GPU with drivers.")
        else:
            logger.info(f"✅ StreamsService initialized (GPU: {gpu_backend})")
        
        # Auto-start streams that were configured with auto_start=True
        # This resumes streams that were running before last shutdown
        logger.info("🔄 Auto-starting configured streams...")
        await container.streams_service.auto_start_configured_streams()
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}", exc_info=True)
        # Don't raise - allow app to start even if auto-start fails
        # Individual streams can be started manually via API

    logger.info("=" * 80)
    logger.info("✅ ProxiMeter started and ready to accept requests")
    logger.info("=" * 80)

    # ========================================================================
    # APPLICATION RUNNING - Yield control back to FastAPI
    # ========================================================================
    
    yield
    
    # ========================================================================
    # SHUTDOWN PHASE
    # ========================================================================
    
    logger.info("=" * 80)
    logger.info("🛑 ProxiMeter shutting down...")
    logger.info("=" * 80)

    # Stop all running streams gracefully
    # This ensures FFmpeg processes are terminated properly before exit
    if container.streams_service is not None:
        try:
            # Get list of all configured streams
            streams_list = await container.streams_service.list_streams()
            
            # Collect stop tasks for all running streams
            stop_tasks = []
            for stream in streams_list:
                if stream.get("status") == "running":
                    stream_name = stream.get("name", "Unknown")
                    stream_id = stream["id"]
                    logger.info(f"🛑 Stopping stream: {stream_name} ({stream_id})")
                    
                    # Create async task to stop this stream
                    stop_tasks.append(
                        container.streams_service.stop_stream(stream_id)
                    )
            
            # Execute all stop operations concurrently
            if stop_tasks:
                logger.info(f"⏳ Waiting for {len(stop_tasks)} streams to stop...")
                results = await asyncio.gather(*stop_tasks, return_exceptions=True)
                
                # Check for errors during shutdown
                errors = [r for r in results if isinstance(r, Exception)]
                if errors:
                    logger.error(f"❌ Errors stopping {len(errors)} streams during shutdown:")
                    for error in errors:
                        logger.error(f"   - {error}")
                else:
                    logger.info(f"✅ Successfully stopped {len(stop_tasks)} streams")
            else:
                logger.info("ℹ️  No running streams to stop")
                
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}", exc_info=True)
    else:
        logger.warning("⚠️  StreamsService was None during shutdown")
    
    logger.info("=" * 80)
    logger.info("✅ ProxiMeter shutdown complete")
    logger.info("=" * 80)


# ============================================================================
# FastAPI Application Configuration
# ============================================================================

app = FastAPI(
    title="ProxiMeter",
    description=(
        "RTSP Stream Management and Zone Detection API with GPU Acceleration.\n\n"
        "Features:\n"
        "- GPU-accelerated FFmpeg stream processing\n"
        "- Real-time MJPEG streaming at 5 FPS\n"
        "- JPEG snapshot capture\n"
        "- Detection zone management (future YOLO integration)\n"
        "- Auto-start streams on boot\n"
        "- Graceful shutdown"
    ),
    version="1.0.0",
    lifespan=lifespan,  # Use modern lifespan context manager
    docs_url="/docs",   # Swagger UI
    redoc_url="/redoc", # ReDoc alternative documentation
    openapi_url="/openapi.json"
)


# ============================================================================
# Exception Handlers
# ============================================================================
# Register standardized exception handlers for consistent error responses
# across all API endpoints. These convert Python exceptions into proper
# HTTP error responses with appropriate status codes and JSON bodies.

app.add_exception_handler(RequestValidationError, validation_exception_handler) # type: ignore
app.add_exception_handler(StarletteHTTPException, http_exception_handler) # type: ignore
app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# Middleware Stack
# ============================================================================
# Middleware is executed in reverse order of registration (last added = first executed)
# Current execution order:
#   1. RequestIDMiddleware - Adds unique X-Request-ID to all requests/responses
#   2. RateLimitMiddleware - Prevents API abuse (5 req/sec, burst of 10)
#   3. (Future) CORS middleware if needed for cross-origin requests

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_second=5.0, burst=10)


# ============================================================================
# API Router Registration
# ============================================================================
# Routers are registered in order of specificity (most specific first)
# to avoid path conflicts. All routers use dependency injection to get
# the singleton StreamsService from the container.

# Health check endpoints (no prefix)
# Routes: /health, /health/live, /health/ready, /health/startup
app.include_router(
    health.router,
    tags=["health"]
)

# Stream management endpoints
# Routes: /api/streams, /api/streams/{id}, /api/streams/{id}/start, etc.
app.include_router(
    streams.router,
    prefix="/api/streams",
    tags=["streams"]
)

# Zone management endpoints (nested under streams)
# Routes: /api/streams/{stream_id}/zones, /api/streams/{stream_id}/zones/{zone_id}
app.include_router(
    zones.router,
    prefix="/api",
    tags=["zones"]
)


# ============================================================================
# Static File Serving for React Frontend
# ============================================================================
# Serves the built React frontend from the static directory.
# This mount MUST be last to avoid overriding API routes.
# The SPA uses HTML5 history mode, so html=True enables fallback to index.html.

STATIC_DIR = os.getenv("STATIC_ROOT", "/app/src/app/static/frontend")

if os.path.exists(STATIC_DIR):
    # Mount static files at root path
    app.mount(
        "/",
        StaticFiles(directory=STATIC_DIR, html=True),
        name="frontend"
    )
    logger.info(f"📁 Serving static files from: {STATIC_DIR}")
else:
    logger.warning(f"⚠️  Static directory not found: {STATIC_DIR}")
    logger.warning("   Frontend will not be available")
    logger.warning("   API endpoints will still work at /api/*")


# ============================================================================
# Application Information Logging
# ============================================================================

logger.info("📝 ProxiMeter application initialized")
logger.info(f"🌍 Environment: {os.getenv('ENV', 'development')}")
logger.info(f"📊 Log level: {os.getenv('LOG_LEVEL', 'INFO')}")
logger.info(f"🔌 Port: {os.getenv('APP_PORT', '8000')}")


# ============================================================================
# API Routes Summary (Documentation)
# ============================================================================

"""
Available API Routes:

Health Checks:
    GET  /health              - Comprehensive health check with system stats
    GET  /health/live         - Kubernetes liveness probe (always 200 OK)
    GET  /health/ready        - Kubernetes readiness probe (checks dependencies)
    GET  /health/startup      - Kubernetes startup probe (checks initialization)

Stream Management:
    GET    /api/streams                     - List all streams
    POST   /api/streams                     - Create new stream
    GET    /api/streams/{id}                - Get stream by ID
    PATCH  /api/streams/{id}                - Update stream (partial)
    PUT    /api/streams/{id}                - Update stream (full)
    DELETE /api/streams/{id}                - Delete stream
    POST   /api/streams/reorder             - Reorder streams for dashboard
    GET    /api/streams/gpu-backend         - Get detected GPU backend info

Stream Control:
    POST   /api/streams/{id}/start          - Start FFmpeg processing
    POST   /api/streams/{id}/stop           - Stop FFmpeg processing

Stream Playback:
    GET    /api/streams/{id}/mjpeg          - MJPEG multipart stream (5fps)
    GET    /api/streams/{id}/snapshot       - JPEG snapshot (single frame)
    GET    /api/streams/{id}/scores         - SSE real-time detection scores

Monitoring:
    GET    /api/streams/metrics             - Prometheus metrics

Zone Management (Future YOLO Integration):
    GET    /api/streams/{stream_id}/zones                - List detection zones
    POST   /api/streams/{stream_id}/zones                - Create detection zone
    GET    /api/streams/{stream_id}/zones/{zone_id}      - Get zone by ID
    PUT    /api/streams/{stream_id}/zones/{zone_id}      - Update zone
    DELETE /api/streams/{stream_id}/zones/{zone_id}      - Delete zone

Interactive Documentation:
    GET  /docs                - Swagger UI (interactive API testing)
    GET  /redoc               - ReDoc (alternative documentation)
    GET  /openapi.json        - OpenAPI 3.0 schema (machine-readable)

Frontend (React SPA):
    GET  /*                   - React frontend (all other routes)

Notes:
    - All API endpoints return JSON (except streaming endpoints)
    - RTSP credentials are masked in all responses for security
    - Rate limit: 5 requests/second with burst of 10
    - All stream operations require GPU backend availability
    - FFmpeg processes are managed by singleton StreamsService
    - Snapshot requests retry up to 3 times with 200ms delay
    - MJPEG streams use multipart/x-mixed-replace content type
"""
