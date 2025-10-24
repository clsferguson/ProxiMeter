"""Zone management service."""

from typing import List, Optional, Dict
from ..config_io import load_config, save_config
from ..models.zone import Zone, NewZone, EditZone
from ..api.errors import raise_not_found

STREAMS_KEY = "streams"
ZONES_KEY = "zones"  # Nested under stream_id

class ZonesService:
    def __init__(self, config_path: str = "/app/config/config.yml"):
        self.config_path = config_path

    async def list_zones(self, stream_id: str) -> List[dict]:
        config = load_config()
        stream_zones = config.get(STREAMS_KEY, {}).get(stream_id, {}).get(ZONES_KEY, [])
        return [Zone(**z).model_dump() for z in stream_zones]

    async def create_zone(self, stream_id: str, new_zone: NewZone) -> dict:
        config = load_config()
        streams = config.get(STREAMS_KEY, {})
        if stream_id not in streams:
            raise ValueError(f"Stream {stream_id} not found")
        
        if ZONES_KEY not in streams[stream_id]:
            streams[stream_id][ZONES_KEY] = []
        
        zone = Zone(stream_id=stream_id, **new_zone.model_dump())
        streams[stream_id][ZONES_KEY].append(zone.model_dump())
        save_config(config)
        return zone.model_dump()

    async def get_zone(self, stream_id: str, zone_id: str) -> Optional[dict]:
        zones = await self.list_zones(stream_id)
        for z in zones:
            if z["id"] == zone_id:
                return z
        return None

    async def update_zone(self, stream_id: str, zone_id: str, edit_zone: EditZone) -> Optional[dict]:
        config = load_config()
        streams = config.get(STREAMS_KEY, {})
        if stream_id not in streams or ZONES_KEY not in streams[stream_id]:
            return None
        
        zones = streams[stream_id][ZONES_KEY]
        for i, z in enumerate(zones):
            if z["id"] == zone_id:
                for key, value in edit_zone.model_dump(exclude_unset=True).items():
                    zones[i][key] = value
                save_config(config)
                return Zone(**zones[i]).model_dump()
        return None

    async def delete_zone(self, stream_id: str, zone_id: str) -> bool:
        config = load_config()
        streams = config.get(STREAMS_KEY, {})
        if stream_id not in streams or ZONES_KEY not in streams[stream_id]:
            return False
        
        zones = streams[stream_id][ZONES_KEY]
        streams[stream_id][ZONES_KEY] = [z for z in zones if z["id"] != zone_id]
        save_config(config)
        return True
