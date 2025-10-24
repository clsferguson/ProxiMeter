"""Zone management service for detection zones within streams."""
from __future__ import annotations

import logging
import uuid
from typing import Final

from ..config_io import load_streams, save_streams
from ..models.zone import Zone, NewZone, EditZone

logger = logging.getLogger(__name__)

ZONES_KEY: Final[str] = "zones"


class ZonesService:
    """Service for managing detection zones within RTSP streams."""
    
    def __init__(self) -> None:
        """Initialize zones service."""
        pass
    
    async def list_zones(self, stream_id: str) -> list[dict]:
        """List all detection zones for a stream."""
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            for stream in streams:
                if stream.get("id") == stream_id:
                    zones = stream.get(ZONES_KEY, [])
                    logger.debug(f"Found {len(zones)} zones for stream {stream_id}")
                    return zones
            
            logger.debug(f"Stream {stream_id} not found")
            return []
            
        except Exception as e:
            logger.error(f"Error listing zones for stream {stream_id}: {e}", exc_info=True)
            return []
    
    async def get_zone(self, stream_id: str, zone_id: str) -> dict | None:
        """Get a specific zone by ID."""
        try:
            zones = await self.list_zones(stream_id)
            
            for zone in zones:
                if zone.get("id") == zone_id:
                    logger.debug(f"Found zone {zone_id} in stream {stream_id}")
                    return zone
            
            logger.debug(f"Zone {zone_id} not found in stream {stream_id}")
            return None
            
        except Exception as e:
            logger.error(
                f"Error getting zone {zone_id} for stream {stream_id}: {e}",
                exc_info=True
            )
            return None
    
    async def create_zone(self, stream_id: str, new_zone: NewZone) -> dict:
        """Create a new detection zone for a stream."""
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            # Find target stream
            stream = self._find_stream(streams, stream_id)
            if not stream:
                raise ValueError(f"Stream {stream_id} not found")
            
            # Initialize zones list if needed
            if ZONES_KEY not in stream:
                stream[ZONES_KEY] = []
            
            # Check for duplicate zone name (case-insensitive)
            self._validate_unique_zone_name(stream, new_zone.name)
            
            # Create zone with UUID
            zone = Zone(
                id=str(uuid.uuid4()),
                stream_id=stream_id,
                **new_zone.model_dump()
            )
            
            # Add to stream and persist
            zone_dict = zone.model_dump()
            stream[ZONES_KEY].append(zone_dict)
            
            config["streams"] = streams
            save_streams(config)
            
            logger.info(f"Created zone {zone.id} in stream {stream_id}")
            return zone_dict
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating zone for stream {stream_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to create zone: {str(e)}")
    
    async def update_zone(
        self,
        stream_id: str,
        zone_id: str,
        edit_zone: EditZone
    ) -> dict | None:
        """Update an existing detection zone."""
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            # Find target stream
            stream = self._find_stream(streams, stream_id)
            if not stream:
                logger.debug(f"Stream {stream_id} not found")
                return None
            
            zones = stream.get(ZONES_KEY, [])
            
            # Find and update zone
            for i, zone in enumerate(zones):
                if zone.get("id") == zone_id:
                    # Check for duplicate name if name is being changed
                    update_data = edit_zone.model_dump(exclude_unset=True)
                    if "name" in update_data:
                        self._validate_unique_zone_name(
                            stream,
                            update_data["name"],
                            exclude_zone_id=zone_id
                        )
                    
                    # Apply updates
                    zones[i].update(update_data)
                    
                    # Validate and persist
                    updated_zone = Zone(**zones[i])
                    
                    config["streams"] = streams
                    save_streams(config)
                    
                    logger.info(f"Updated zone {zone_id} in stream {stream_id}")
                    return updated_zone.model_dump()
            
            logger.debug(f"Zone {zone_id} not found in stream {stream_id}")
            return None
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Error updating zone {zone_id} in stream {stream_id}: {e}",
                exc_info=True
            )
            raise ValueError(f"Failed to update zone: {str(e)}")
    
    async def delete_zone(self, stream_id: str, zone_id: str) -> bool:
        """Delete a detection zone."""
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            # Find target stream
            stream = self._find_stream(streams, stream_id)
            if not stream:
                logger.debug(f"Stream {stream_id} not found")
                return False
            
            zones = stream.get(ZONES_KEY, [])
            original_length = len(zones)
            
            # Filter out the zone
            stream[ZONES_KEY] = [z for z in zones if z.get("id") != zone_id]
            
            # Check if anything was deleted
            if len(stream[ZONES_KEY]) < original_length:
                config["streams"] = streams
                save_streams(config)
                logger.info(f"Deleted zone {zone_id} from stream {stream_id}")
                return True
            
            logger.debug(f"Zone {zone_id} not found in stream {stream_id}")
            return False
            
        except Exception as e:
            logger.error(
                f"Error deleting zone {zone_id} from stream {stream_id}: {e}",
                exc_info=True
            )
            return False
    
    def _find_stream(self, streams: list[dict], stream_id: str) -> dict | None:
        """Find stream by ID in streams list."""
        for stream in streams:
            if stream.get("id") == stream_id:
                return stream
        return None
    
    def _validate_unique_zone_name(
        self,
        stream: dict,
        name: str,
        exclude_zone_id: str | None = None
    ) -> None:
        """Validate zone name is unique within stream (case-insensitive)."""
        from ..utils.strings import normalize_stream_name
        
        normalized_name = normalize_stream_name(name)
        zones = stream.get(ZONES_KEY, [])
        
        for zone in zones:
            # Skip the zone being updated
            if exclude_zone_id and zone.get("id") == exclude_zone_id:
                continue
            
            if normalize_stream_name(zone.get("name", "")) == normalized_name:
                raise ValueError(
                    f"Zone name '{name}' already exists in this stream "
                    "(case-insensitive)"
                )
