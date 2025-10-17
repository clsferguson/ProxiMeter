"""FastAPI ASGI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

# Template configuration
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Static files will be mounted after routers are added
static_dir = Path(__file__).parent / "static"

# Placeholder for routers - will be wired in T020
# TODO: Add routers for health, streams API, and UI views

logger.info("FastAPI app initialized")
