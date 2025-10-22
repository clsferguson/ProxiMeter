"""UI view handlers for React SPA frontend.

This module serves the React SPA frontend built in frontend/src.
The frontend is a single-page application that handles all routing client-side.
The backend only serves the index.html for all non-API routes.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ui"])

# Path to the built React frontend
STATIC_DIR = Path(__file__).parent.parent / "static" / "frontend"
INDEX_HTML = STATIC_DIR / "index.html"


@router.get("/", response_class=FileResponse)
async def serve_frontend_root():
    """Serve the React SPA index.html at root path."""
    if not INDEX_HTML.exists():
        logger.error(f"Frontend index.html not found at {INDEX_HTML}")
        return {"error": "Frontend not found"}
    return FileResponse(INDEX_HTML)


@router.get("/{path:path}", response_class=FileResponse)
async def serve_frontend_spa(path: str):
    """
    Serve the React SPA for all non-API routes.
    
    This catch-all route ensures that all frontend routes are handled by React Router.
    API routes are handled by the /api prefix and won't reach this handler.
    Static assets (CSS, JS, fonts) are served from the dist directory.
    
    Args:
        path: The requested path
        
    Returns:
        FileResponse: The requested file or index.html for SPA routing
    """
    # Don't serve API routes through this handler
    if path.startswith("api/"):
        return {"error": "Not found"}
    
    # Try to serve the requested file from static directory
    file_path = STATIC_DIR / path
    
    # Security check: ensure the file is within STATIC_DIR
    try:
        file_path.resolve().relative_to(STATIC_DIR.resolve())
    except ValueError:
        # Path is outside STATIC_DIR, serve index.html for SPA routing
        if INDEX_HTML.exists():
            return FileResponse(INDEX_HTML)
        return {"error": "Frontend not found"}
    
    # If file exists and is a file, serve it
    if file_path.is_file():
        return FileResponse(file_path)
    
    # For any other path, serve index.html (SPA routing)
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    
    logger.error(f"Frontend index.html not found at {INDEX_HTML}")
    return {"error": "Frontend not found"}
