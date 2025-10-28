"""Zone management service for detection zones within streams.

Detection zones define polygonal regions for person detection scoring.
Zones are stored within their parent stream configuration in YAML.

Zone Operations:
    - CRUD operations on detection zones
    - Nested storage (zones within streams)
    - Case-insensitive name uniqueness per stream
    - Polygon coordinate validation via Pydantic models

Constitution Compliance:
    - Normalized coordinates (0.0-1.0) for resolution independence
    - Polygon-based zones for Shapely integration
    - Supports future YOLO + Shapely detection scoring

Logging Strategy:
    DEBUG - Zone lookups, validation checks
    INFO  - Zone lifecycle (create/update/delete)
    WARN  - Validation failures (logged before exception)
    ERROR - Unexpected errors with stack traces
"""
from __future__ import annotations

import logging
import uuid
from typing import Final

from ..config_io import load_streams, save_streams
from ..models.zone import Zone, NewZone, EditZone
from ..utils.strings import normalize_stream_name

logger = logging.getLogger(__name__)

ZONES_KEY: Final[str] = "zones"
"""Key for zones array within stream config."""


class ZonesService:
    """Service for managing detection zones within RTSP streams.
    
    Zones are stored within their parent stream in YAML:
        streams:
          - id: stream-uuid
            zones:
              - id: zone-uuid
                name: "Entry Zone"
                coordinates: [[0.1, 0.1], [0.9, 0.1], ...]
    """
    
    async def list_zones(self, stream_id: str) -> list[dict]:
        """List all detection zones for a stream.
        
        Args:
            stream_id: Parent stream UUID
            
        Returns:
            List of zone dicts (empty if stream not found)
        """
        try:
            config = load_streams()
            
            for stream in config.get("streams", []):
                if stream.get("id") == stream_id:
                    zones = stream.get(ZONES_KEY, [])
                    logger.debug(f"Listed {len(zones)} zone(s) for stream {stream_id}")
                    return zones
            
            logger.debug(f"Stream not found: {stream_id}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to list zones for {stream_id}: {e}", exc_info=True)
            return []
    
    async def get_zone(self, stream_id: str, zone_id: str) -> dict | None:
        """Get specific zone by ID.
        
        Args:
            stream_id: Parent stream UUID
            zone_id: Zone UUID
            
        Returns:
            Zone dict or None if not found
        """
        try:
            zones = await self.list_zones(stream_id)
            
            for zone in zones:
                if zone.get("id") == zone_id:
                    return zone
            
            logger.debug(f"Zone not found: {zone_id} in stream {stream_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get zone {zone_id} in {stream_id}: {e}", exc_info=True)
            return None
    
    async def create_zone(self, stream_id: str, new_zone: NewZone) -> dict:
        """Create new detection zone for stream.
        
        Args:
            stream_id: Parent stream UUID
            new_zone: Zone configuration with name and coordinates
            
        Returns:
            Created zone dict with generated UUID
            
        Raises:
            ValueError: Stream not found or duplicate name
        """
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            # Find stream
            stream = self._find_stream(streams, stream_id)
            if not stream:
                logger.warning(f"Cannot create zone - stream not found: {stream_id}")
                raise ValueError(f"Stream {stream_id} not found")
            
            # Initialize zones if needed
            if ZONES_KEY not in stream:
                stream[ZONES_KEY] = []
            
            # Validate unique name
            self._validate_unique_zone_name(stream, new_zone.name)
            
            # Create zone
            zone = Zone(
                id=str(uuid.uuid4()),
                stream_id=stream_id,
                **new_zone.model_dump()
            )
            
            # Add and persist
            zone_dict = zone.model_dump()
            stream[ZONES_KEY].append(zone_dict)
            config["streams"] = streams
            save_streams(config)
            
            logger.info(f"Created zone: {new_zone.name} ({zone.id}) in stream {stream_id}")
            return zone_dict
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create zone in {stream_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to create zone: {str(e)}")
    
    async def update_zone(
        self,
        stream_id: str,
        zone_id: str,
        edit_zone: EditZone
    ) -> dict | None:
        """Update existing detection zone.
        
        Args:
            stream_id: Parent stream UUID
            zone_id: Zone UUID
            edit_zone: Partial update data
            
        Returns:
            Updated zone dict or None if not found
            
        Raises:
            ValueError: Validation failure (duplicate name)
        """
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            # Find stream
            stream = self._find_stream(streams, stream_id)
            if not stream:
                logger.debug(f"Update failed - stream not found: {stream_id}")
                return None
            
            zones = stream.get(ZONES_KEY, [])
            
            # Find and update zone
            for i, zone in enumerate(zones):
                if zone.get("id") == zone_id:
                    # Validate unique name if changing
                    update_data = edit_zone.model_dump(exclude_unset=True)
                    if "name" in update_data:
                        self._validate_unique_zone_name(
                            stream,
                            update_data["name"],
                            exclude_zone_id=zone_id
                        )
                    
                    # Apply updates
                    zones[i].update(update_data)
                    
                    # Re-validate with Pydantic
                    updated_zone = Zone(**zones[i])
                    
                    # Persist
                    config["streams"] = streams
                    save_streams(config)
                    
                    logger.info(f"Updated zone: {zone_id} in stream {stream_id}")
                    return updated_zone.model_dump()
            
            logger.debug(f"Update failed - zone not found: {zone_id} in {stream_id}")
            return None
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update zone {zone_id} in {stream_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to update zone: {str(e)}")
    
    async def delete_zone(self, stream_id: str, zone_id: str) -> bool:
        """Delete detection zone.
        
        Args:
            stream_id: Parent stream UUID
            zone_id: Zone UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            config = load_streams()
            streams = config.get("streams", [])
            
            # Find stream
            stream = self._find_stream(streams, stream_id)
            if not stream:
                logger.debug(f"Delete failed - stream not found: {stream_id}")
                return False
            
            zones = stream.get(ZONES_KEY, [])
            original_count = len(zones)
            
            # Remove zone
            stream[ZONES_KEY] = [z for z in zones if z.get("id") != zone_id]
            
            # Check if deleted
            if len(stream[ZONES_KEY]) < original_count:
                config["streams"] = streams
                save_streams(config)
                logger.info(f"Deleted zone: {zone_id} from stream {stream_id}")
                return True
            
            logger.debug(f"Delete failed - zone not found: {zone_id} in {stream_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete zone {zone_id} from {stream_id}: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
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
        """Validate zone name is unique within stream (case-insensitive).
        
        Args:
            stream: Parent stream dict
            name: Zone name to validate
            exclude_zone_id: Zone ID to exclude (for updates)
            
        Raises:
            ValueError: If name already exists
        """
        normalized_name = normalize_stream_name(name)
        zones = stream.get(ZONES_KEY, [])
        
        for zone in zones:
            # Skip zone being updated
            if exclude_zone_id and zone.get("id") == exclude_zone_id:
                continue
            
            if normalize_stream_name(zone.get("name", "")) == normalized_name:
                logger.warning(f"Duplicate zone name: '{name}' in stream {stream.get('id')}")
                raise ValueError(f"Zone name '{name}' already exists in this stream")


logger.debug("ZonesService module loaded")
