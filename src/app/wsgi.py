"""FastAPI ASGI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
import logging
from pathlib import Path

# Configure logging first
from .logging_config import configure_logging
configure_logging()

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ProxiMeter",
    version="0.2.0",
    docs_url=None,  # Disable docs for LAN-only deployment
    redoc_url=None,
)

# Import routers
from .api import health, streams
from .ui import views

# Import middleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_id import RequestIDMiddleware

# Import error handlers
from .api.errors import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)

# Add middleware (order matters: last added = first executed)
# 1. Request ID (first to execute, adds ID to all requests)
app.add_middleware(RequestIDMiddleware)

# 2. Rate limiting (after request ID, before business logic)
app.add_middleware(RateLimitMiddleware, requests_per_second=5.0, burst=10)

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
# Health endpoint (no prefix)
app.include_router(health.router)

# API endpoints
app.include_router(streams.router)

# UI views (no prefix, serves from root)
app.include_router(views.router)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Template configuration (for reference, actual templates configured in views.py)
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

logger.info("FastAPI app initialized with routers and middleware")
