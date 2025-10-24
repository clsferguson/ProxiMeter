"""FastAPI application entry point."""
from typing import Callable
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import os

from .api import health, streams, zones
from .logging_config import setup_logging

logger = logging.getLogger(__name__)

# Setup logging
setup_logging()

app = FastAPI(
    title="ProxiMeter",
    description="RTSP Stream Management and Zone Detection API",
    version="1.0.0"
)

# Exception handlers
async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": str(exc.body) if exc.body else None}
    )

async def http_exception_handler(
    request: Request, 
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Register exception handlers - cast to the correct type
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore

# Include routers
app.include_router(health.router)
app.include_router(streams.router, prefix="/api")
app.include_router(zones.router, prefix="/api")

# Get static directory from environment or use default
static_dir = os.getenv("STATIC_ROOT", "/app/src/app/static/frontend")

# Serve static files (frontend) - must be last
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    logger.info(f"Serving static files from: {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")

logger.info("ProxiMeter application initialized")

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("ProxiMeter starting up...")
    logger.info("API documentation available at /docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("ProxiMeter shutting down...")
