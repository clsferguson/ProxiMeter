"""UI view handlers for template rendering."""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

from app.services.streams_service import StreamsService
from app.utils.strings import mask_rtsp_credentials

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ui"])

# Templates will be configured in wsgi.py
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Render the landing page with stream list."""
    service = StreamsService()
    streams = await service.list_streams()
    
    # Mask credentials in URLs for display
    for stream in streams:
        if "rtsp_url" in stream:
            stream["rtsp_url_masked"] = mask_rtsp_credentials(stream["rtsp_url"])
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "streams": streams
    })


@router.get("/streams/new", response_class=HTMLResponse)
async def add_stream_form(request: Request):
    """Render the add stream form."""
    return templates.TemplateResponse("add_stream.html", {
        "request": request,
        "error": None,
        "name": "",
        "rtsp_url": ""
    })


@router.post("/streams/new")
async def add_stream_submit(
    request: Request,
    name: str = Form(...),
    rtsp_url: str = Form(...)
):
    """Handle add stream form submission."""
    service = StreamsService()
    
    try:
        # Create the stream
        stream = await service.create_stream(name=name, rtsp_url=rtsp_url)
        
        # Redirect to playback page
        stream_id = stream.get("id")
        return RedirectResponse(url=f"/play/{stream_id}", status_code=303)
        
    except ValueError as e:
        # Validation error - re-render form with error
        return templates.TemplateResponse("add_stream.html", {
            "request": request,
            "error": str(e),
            "name": name,
            "rtsp_url": rtsp_url
        }, status_code=400)
    except Exception as e:
        logger.error(f"Error creating stream: {e}", exc_info=True)
        return templates.TemplateResponse("add_stream.html", {
            "request": request,
            "error": "An unexpected error occurred. Please try again.",
            "name": name,
            "rtsp_url": rtsp_url
        }, status_code=500)


@router.get("/play/{stream_id}", response_class=HTMLResponse)
async def playback_page(request: Request, stream_id: str):
    """Render the playback page for a stream."""
    service = StreamsService()
    stream = await service.get_stream(stream_id)
    
    if not stream:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Stream not found: {stream_id}"
        }, status_code=404)
    
    # Mask credentials for display
    stream["rtsp_url_masked"] = mask_rtsp_credentials(stream.get("rtsp_url", ""))
    
    return templates.TemplateResponse("play.html", {
        "request": request,
        "stream": stream
    })
