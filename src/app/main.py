"""FastAPI application entry point.

ProxiMeter RTSP Stream Management API with GPU-accelerated video processing.

This module initializes the FastAPI application, sets up middleware, registers
API routers, and manages the application lifecycle including FFmpeg subprocess
management for RTSP stream processing.

CRITICAL: Uses a singleton StreamsService instance to persist FFmpeg processes
across API requests. Each request must use the SAME service instance, otherwise
the active_processes dict will be empty and snapshots will fail.

Constitution-compliant:
- GPU-only operation (no CPU fallback)
- FFmpeg for all stream processing
- Automatic stream startup on boot
- Graceful shutdown of all streams
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

logger = logging.getLogger(__name__)

# Setup logging before anything else
setup_logging()


# ============================================================================
# Global Service Instance (CRITICAL FIX)
# ============================================================================

# This is the SINGLE StreamsService instance that persists for the entire
# application lifetime. All API requests MUST use this same instance.
#
# WHY THIS IS CRITICAL:
# - StreamsService stores FFmpeg processes in active_processes dict
# - If each request creates a new instance, active_processes is empty
# - Snapshot requests fail with "Stream not in active_processes"
# - This was the root cause of the bug where processes existed but weren't found
#
# This singleton pattern ensures that:
# 1. FFmpeg processes started in create_stream() are stored
# 2. Snapshot requests in get_snapshot() can find those processes
# 3. All requests see the same state
streams_service_instance: StreamsService | None = None


def get_streams_service() -> StreamsService:
    """Get the global StreamsService singleton instance.
    
    This dependency is injected into all API route handlers to ensure
    they all use the SAME service instance with the SAME active_processes dict.
    
    Returns:
        The global StreamsService instance
        
    Raises:
        RuntimeError: If called before application startup completes
    """
    if streams_service_instance is None:
        raise RuntimeError(
            "StreamsService not initialized. "
            "This should never happen if lifespan context is working correctly."
        )
    return streams_service_instance


# ============================================================================
# Application Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.
    
    Handles startup and shutdown events using modern FastAPI pattern.
    
    Startup:
    - Creates the singleton StreamsService instance
    - Auto-starts streams with auto_start=True
    - Validates GPU backend availability
    
    Shutdown:
    - Gracefully stops all running FFmpeg processes
    - Cleans up resources
    - Logs shutdown status
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    
    logger.info("🚀 ProxiMeter starting up...")
    logger.info("📚 API documentation available at /docs")
    
    # CRITICAL: Create the singleton StreamsService instance
    # This instance persists for the entire application lifetime
    global streams_service_instance
    
    try:
        # Initialize the service (validates GPU backend)
        streams_service_instance = StreamsService()
        logger.info(f"✅ StreamsService initialized (GPU: {streams_service_instance.gpu_backend})")
        
        # Auto-start configured streams
        # This resumes streams that were running before last shutdown
        await streams_service_instance.auto_start_configured_streams()
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}", exc_info=True)
        # Don't raise - allow app to start even if auto-start fails
        # Individual streams can be started manually via API

    logger.info("✅ ProxiMeter started and ready")

    # ========================================================================
    # APPLICATION RUNNING - Yield control back to FastAPI
    # ========================================================================
    
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    
    logger.info("🛑 ProxiMeter shutting down...")

    # Stop all running streams gracefully
    # This ensures FFmpeg processes are terminated properly
    if streams_service_instance is not None:
        try:
            streams = await streams_service_instance.list_streams()
            
            # Collect stop tasks for all running streams
            stop_tasks = []
            for stream in streams:
                if stream.get("status") == "running":
                    logger.info(f"Stopping stream: {stream.get('name')} ({stream['id']})")
                    stop_tasks.append(
                        streams_service_instance.stop_stream(stream["id"])
                    )
            
            # Execute all stops concurrently
            if stop_tasks:
                results = await asyncio.gather(*stop_tasks, return_exceptions=True)
                
                # Log any errors during shutdown
                errors = [r for r in results if isinstance(r, Exception)]
                if errors:
                    logger.error(f"Errors stopping {len(errors)} streams during shutdown")
                else:
                    logger.info(f"✅ Successfully stopped {len(stop_tasks)} streams")
            else:
                logger.info("No running streams to stop")
                
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}", exc_info=True)
    else:
        logger.warning("StreamsService was None during shutdown")
    
    logger.info("✅ ProxiMeter shutdown complete")


# ============================================================================
# Application Configuration
# ============================================================================

app = FastAPI(
    title="ProxiMeter",
    description="RTSP Stream Management and Zone Detection API with GPU Acceleration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# Exception Handlers
# ============================================================================

# Register standardized exception handlers for consistent error responses
app.add_exception_handler(RequestValidationError, validation_exception_handler) # type: ignore
app.add_exception_handler(StarletteHTTPException, http_exception_handler) # type: ignore
app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# Middleware
# ============================================================================

# Register middleware in reverse order (last added = first executed)
# 1. RequestIDMiddleware adds unique request ID to logs
# 2. RateLimitMiddleware prevents API abuse
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_second=5.0, burst=10)


# ============================================================================
# API Routers
# ============================================================================

# Health check endpoints (no prefix)
app.include_router(
    health.router,
    tags=["health"]
)

# Stream management endpoints
app.include_router(
    streams.router,
    prefix="/api/streams",
    tags=["streams"]
)

# Zone management endpoints (includes /streams/{stream_id}/zones in path)
app.include_router(
    zones.router,
    prefix="/api",
    tags=["zones"]
)


# ============================================================================
# Static File Serving
# ============================================================================

# Get static directory from environment or use default
STATIC_DIR = os.getenv("STATIC_ROOT", "/app/src/app/static/frontend")

# Serve frontend static files (must be last to not override API routes)
if os.path.exists(STATIC_DIR):
    app.mount(
        "/",
        StaticFiles(directory=STATIC_DIR, html=True),
        name="frontend"
    )
    logger.info(f"📁 Serving static files from: {STATIC_DIR}")
else:
    logger.warning(f"⚠️  Static directory not found: {STATIC_DIR}")
    logger.warning("Frontend will not be available")


# ============================================================================
# Application Info
# ============================================================================

logger.info("ProxiMeter application initialized")
logger.info(f"Environment: {os.getenv('ENV', 'development')}")
logger.info(f"Log level: {os.getenv('LOG_LEVEL', 'INFO')}")


# ============================================================================
# API Routes Summary
# ============================================================================

"""
Available API Routes:

Health:
    GET  /health              - Comprehensive health check
    GET  /health/live         - Kubernetes liveness probe
    GET  /health/ready        - Kubernetes readiness probe
    GET  /health/startup      - Kubernetes startup probe

Streams:
    GET    /api/streams                     - List all streams
    POST   /api/streams                     - Create stream
    GET    /api/streams/{id}                - Get stream
    PUT    /api/streams/{id}                - Update stream
    DELETE /api/streams/{id}                - Delete stream
    POST   /api/streams/{id}/start          - Start stream
    POST   /api/streams/{id}/stop           - Stop stream
    POST   /api/streams/reorder             - Reorder streams
    GET    /api/streams/{id}/mjpeg          - MJPEG stream
    GET    /api/streams/{id}/snapshot       - JPEG snapshot
    GET    /api/streams/{id}/scores         - SSE detection scores
    GET    /api/streams/gpu-backend         - Get GPU backend
    GET    /api/streams/metrics             - Prometheus metrics

Zones:
    GET    /api/streams/{stream_id}/zones                - List zones
    POST   /api/streams/{stream_id}/zones                - Create zone
    GET    /api/streams/{stream_id}/zones/{zone_id}      - Get zone
    PUT    /api/streams/{stream_id}/zones/{zone_id}      - Update zone
    DELETE /api/streams/{stream_id}/zones/{zone_id}      - Delete zone

Documentation:
    GET  /docs                - Swagger UI
    GET  /redoc               - ReDoc UI
    GET  /openapi.json        - OpenAPI schema
"""