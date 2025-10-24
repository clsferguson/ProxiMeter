"""FastAPI application entry point."""
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import health, streams, zones
from .api.errors import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from .logging_config import setup_logging

logger = logging.getLogger(__name__)

# Setup logging before anything else
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.
    
    Handles startup and shutdown events using modern FastAPI pattern.
    """
    # Startup
    logger.info("ProxiMeter starting up...")
    logger.info("API documentation available at /docs")
    
    yield
    
    # Shutdown
    logger.info("ProxiMeter shutting down...")


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
    logger.info(f"Serving static files from: {STATIC_DIR}")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")
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
    POST   /api/streams/reorder              - Reorder streams
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
