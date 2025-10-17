"""Stream management service with business logic."""
from typing import List, Optional
import logging
from datetime import datetime
import uuid

from app.config_io import load_streams, save_streams
from app.models.stream import Stream, NewStream
from app.utils.validation import validate_rtsp_url
from app.utils.strings import normalize_stream_name
from app.utils.rtsp import probe_rtsp_stream

logger = logging.getLogger(__name__)


class StreamsService:
    """Service for managing streams with validation and persistence."""
    
    def __init__(self, config_path: str = "/app/config/config.yml"):
        """Initialize the streams service.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        logger.info(f"StreamsService initialized with config: {config_path}")
    
    async def list_streams(self) -> List[dict]:
        """List all streams.
        
        Returns:
            List of stream dictionaries sorted by order
        """
        streams = load_streams()
        # Sort by order field
        streams.sort(key=lambda s: s.get("order", 0))
        return streams
    
    async def create_stream(self, name: str, rtsp_url: str) -> dict:
        """Create a new stream with validation.
        
        Args:
            name: Stream name (1-50 chars, unique CI)
            rtsp_url: RTSP URL starting with rtsp://
            
        Returns:
            Created stream dictionary
            
        Raises:
            ValueError: If validation fails
        """
        # Validate and normalize inputs
        name = name.strip()
        rtsp_url = rtsp_url.strip()
        
        if not name or len(name) > 50:
            raise ValueError("Name must be 1-50 characters after trimming")
        
        # Validate RTSP URL format
        is_valid, error_msg = validate_rtsp_url(rtsp_url)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Load existing streams
        streams = load_streams()
        
        # Check for duplicate name (case-insensitive)
        normalized_name = normalize_stream_name(name)
        for stream in streams:
            if normalize_stream_name(stream.get("name", "")) == normalized_name:
                raise ValueError(f"Stream name '{name}' already exists (case-insensitive)")
        
        # Probe RTSP stream (2s timeout)
        logger.info(f"Probing RTSP stream: {rtsp_url}")
        is_reachable = await probe_rtsp_stream(rtsp_url, timeout_seconds=2.0)
        
        # Create stream object
        stream = Stream(
            id=str(uuid.uuid4()),
            name=name,
            rtsp_url=rtsp_url,
            created_at=datetime.utcnow().isoformat() + "Z",
            order=len(streams),
            status="Active" if is_reachable else "Inactive"
        )
        
        # Add to streams list and save
        streams.append(stream.model_dump())
        save_streams(streams)
        
        logger.info(f"Created stream {stream.id} with status {stream.status}")
        return stream.model_dump()
    
    async def get_stream(self, stream_id: str) -> Optional[dict]:
        """Get a stream by ID.
        
        Args:
            stream_id: Stream UUID
            
        Returns:
            Stream dictionary or None if not found
        """
        streams = load_streams()
        for stream in streams:
            if stream.get("id") == stream_id:
                return stream
        return None
    
    async def update_stream(self, stream_id: str, name: Optional[str] = None, 
                          rtsp_url: Optional[str] = None) -> Optional[dict]:
        """Update a stream (partial update).
        
        Args:
            stream_id: Stream UUID
            name: New name (optional)
            rtsp_url: New RTSP URL (optional)
            
        Returns:
            Updated stream dictionary or None if not found
        """
        # TODO: Implement in T042
        return None
    
    async def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream and renumber orders.
        
        Args:
            stream_id: Stream UUID
            
        Returns:
            True if deleted, False if not found
        """
        # TODO: Implement in T041
        return False
    
    async def reorder_streams(self, order: List[str]) -> bool:
        """Reorder streams by ID list.
        
        Args:
            order: List of stream UUIDs in desired order
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If order is invalid
        """
        # TODO: Implement in T043
        raise NotImplementedError("Reorder not yet implemented")
