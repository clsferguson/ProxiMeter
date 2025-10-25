"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
import logging
import os

from fastapi import FastAPI
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.
    
    Handles startup and shutdown events using modern FastAPI pattern.
    """
    # Startup
    logger.info("ProxiMeter starting up...")
    logger.info("API documentation available at /docs")
    
    # Auto-start configured streams
    try:
        service = StreamsService()
        await service.auto_start_configured_streams()
    except Exception as e:
        logger.error(f"Error during auto-start: {e}", exc_info=True)

    logger.info("ProxiMeter started")

    yield
    
    # Shutdown
    logger.info("ProxiMeter shutting down...")

    # Stop all running streams
    try:
        service = StreamsService()
        streams = await service.list_streams()
        
        stop_tasks = []
        for stream in streams:
            if stream.get("status") == "running":
                stop_tasks.append(service.stop_stream(stream["id"]))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
            logger.info(f"Stopped {len(stop_tasks)} streams")
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)
    
    logger.info("ProxiMeter shutdown complete")

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

# Register standardized exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler) # type: ignore
app.add_exception_handler(StarletteHTTPException, http_exception_handler) # type: ignore
app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# Middleware
# ============================================================================

# Register rate limiting and request ID middleware
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
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    return {"name": "ProxiMeter API", "version": "1.0.0", "status": "operational"}

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
