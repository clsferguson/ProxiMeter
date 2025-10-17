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
            
        Raises:
            ValueError: If validation fails
        """
        # Load existing streams
        streams = load_streams()
        
        # Find the stream to update
        stream_index = None
        for i, stream in enumerate(streams):
            if stream.get("id") == stream_id:
                stream_index = i
                break
        
        if stream_index is None:
            return None
        
        stream = streams[stream_index]
        url_changed = False
        
        # Update name if provided
        if name is not None:
            name = name.strip()
            if not name or len(name) > 50:
                raise ValueError("Name must be 1-50 characters after trimming")
            
            # Check for duplicate name (case-insensitive), excluding current stream
            normalized_name = normalize_stream_name(name)
            for i, s in enumerate(streams):
                if i != stream_index and normalize_stream_name(s.get("name", "")) == normalized_name:
                    raise ValueError(f"Stream name '{name}' already exists (case-insensitive)")
            
            stream["name"] = name
        
        # Update RTSP URL if provided
        if rtsp_url is not None:
            rtsp_url = rtsp_url.strip()
            
            # Validate RTSP URL format
            is_valid, error_msg = validate_rtsp_url(rtsp_url)
            if not is_valid:
                raise ValueError(error_msg)
            
            stream["rtsp_url"] = rtsp_url
            url_changed = True
        
        # Re-probe if URL changed
        if url_changed:
            logger.info(f"Re-probing RTSP stream {stream_id} after URL change")
            is_reachable = await probe_rtsp_stream(stream["rtsp_url"], timeout_seconds=2.0)
            stream["status"] = "Active" if is_reachable else "Inactive"
            logger.info(f"Stream {stream_id} status updated to {stream['status']}")
        
        # Save updated streams
        streams[stream_index] = stream
        save_streams(streams)
        
        logger.info(f"Updated stream {stream_id}")
        return stream
    
    async def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream and renumber orders.
        
        Args:
            stream_id: Stream UUID
            
        Returns:
            True if deleted, False if not found
        """
        # Load existing streams
        streams = load_streams()
        
        # Find and remove the stream
        stream_found = False
        for i, stream in enumerate(streams):
            if stream.get("id") == stream_id:
                streams.pop(i)
                stream_found = True
                logger.info(f"Deleted stream {stream_id}")
                break
        
        if not stream_found:
            return False
        
        # Renumber remaining streams (contiguous ordering starting at 0)
        for i, stream in enumerate(streams):
            stream["order"] = i
        
        # Save updated streams
        save_streams(streams)
        
        logger.info(f"Renumbered {len(streams)} remaining streams")
        return True
    
    async def reorder_streams(self, order: List[str]) -> bool:
        """Reorder streams by ID list.
        
        Args:
            order: List of stream UUIDs in desired order
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If order is invalid (duplicates, missing IDs)
        """
        # Load existing streams
        streams = load_streams()
        
        # No-op if 0 or 1 streams
        if len(streams) <= 1:
            logger.info("Reorder no-op: ≤1 streams")
            return True
        
        # Validate order list
        if len(order) != len(streams):
            raise ValueError(f"Order list must contain exactly {len(streams)} stream IDs")
        
        # Check for duplicates
        if len(set(order)) != len(order):
            raise ValueError("Order list contains duplicate IDs")
        
        # Build a map of existing streams by ID
        stream_map = {s.get("id"): s for s in streams}
        
        # Validate all IDs exist
        for stream_id in order:
            if stream_id not in stream_map:
                raise ValueError(f"Unknown stream ID in order list: {stream_id}")
        
        # Check if order is already the same (idempotent)
        current_order = [s.get("id") for s in streams]
        if current_order == order:
            logger.info("Reorder no-op: order unchanged")
            return True
        
        # Reorder streams according to the provided list
        reordered_streams = []
        for i, stream_id in enumerate(order):
            stream = stream_map[stream_id].copy()
            stream["order"] = i
            reordered_streams.append(stream)
        
        # Save reordered streams
        save_streams(reordered_streams)
        
        logger.info(f"Reordered {len(reordered_streams)} streams")
        return True
