"""UI view handlers for template rendering."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ui"])

# Templates will be configured in wsgi.py
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Render the landing page with stream list."""
    # TODO: Implement in T032
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/streams/new", response_class=HTMLResponse)
async def add_stream_form(request: Request):
    """Render the add stream form."""
    # TODO: Implement in T033
    return templates.TemplateResponse("add_stream.html", {"request": request})


@router.get("/play/{stream_id}.mjpg")
async def playback_stream(stream_id: str):
    """Stream MJPEG playback."""
    # TODO: Implement in T031
    pass
