"""Zone management service."""
from typing import List, Optional
import uuid

from ..config_io import load_streams, save_streams
from ..models.zone import Zone, NewZone, EditZone

ZONES_KEY = "zones"

class ZonesService:
    """Service for managing detection zones within streams."""
    
    def __init__(self, config_path: str = "/app/config/config.yml"):
        self.config_path = config_path
    
    async def list_zones(self, stream_id: str) -> List[dict]:
        """List all zones for a stream."""
        streams = load_streams()
        
        for stream in streams:
            if stream.get("id") == stream_id:
                return stream.get(ZONES_KEY, [])
        
        return []
    
    async def create_zone(self, stream_id: str, new_zone: NewZone) -> dict:
        """Create a new zone for a stream."""
        streams = load_streams()
        
        for stream in streams:
            if stream.get("id") == stream_id:
                if ZONES_KEY not in stream:
                    stream[ZONES_KEY] = []
                
                zone = Zone(
                    id=str(uuid.uuid4()),
                    stream_id=stream_id,
                    **new_zone.model_dump()
                )
                zone_dict = zone.model_dump()
                stream[ZONES_KEY].append(zone_dict)
                
                save_streams(streams)
                return zone_dict
        
        raise ValueError(f"Stream {stream_id} not found")
    
    async def get_zone(self, stream_id: str, zone_id: str) -> Optional[dict]:
        """Get a specific zone by ID."""
        zones = await self.list_zones(stream_id)
        
        for zone in zones:
            if zone.get("id") == zone_id:
                return zone
        
        return None
    
    async def update_zone(
        self,
        stream_id: str,
        zone_id: str,
        edit_zone: EditZone
    ) -> Optional[dict]:
        """Update a zone."""
        streams = load_streams()
        
        for stream in streams:
            if stream.get("id") == stream_id:
                zones = stream.get(ZONES_KEY, [])
                
                for i, zone in enumerate(zones):
                    if zone.get("id") == zone_id:
                        for key, value in edit_zone.model_dump(exclude_unset=True).items():
                            zones[i][key] = value
                        
                        save_streams(streams)
                        return Zone(**zones[i]).model_dump()
        
        return None
    
    async def delete_zone(self, stream_id: str, zone_id: str) -> bool:
        """Delete a zone."""
        streams = load_streams()
        
        for stream in streams:
            if stream.get("id") == stream_id:
                zones = stream.get(ZONES_KEY, [])
                original_length = len(zones)
                stream[ZONES_KEY] = [z for z in zones if z.get("id") != zone_id]
                
                if len(stream[ZONES_KEY]) < original_length:
                    save_streams(streams)
                    return True
        
        return False
