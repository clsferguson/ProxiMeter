"""REST API endpoints for zone management."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import logging

from ..services.zones_service import ZonesService
from ..models.zone import Zone, NewZone, EditZone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/streams/{stream_id}/zones", tags=["zones"])

def get_zones_service() -> ZonesService:
    """Dependency to get zones service instance."""
    return ZonesService()

@router.get("", response_model=List[Zone])
async def list_zones(
    stream_id: str,
    service: ZonesService = Depends(get_zones_service)
):
    """List all zones for a stream."""
    return await service.list_zones(stream_id)

@router.post("", response_model=Zone, status_code=status.HTTP_201_CREATED)
async def create_zone(
    stream_id: str,
    new_zone: NewZone,
    service: ZonesService = Depends(get_zones_service)
):
    """Create a new zone for a stream."""
    try:
        zone = await service.create_zone(stream_id, new_zone)
        return zone
    except ValueError as e:
        logger.error(f"Error creating zone: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{zone_id}", response_model=Zone)
async def get_zone(
    stream_id: str,
    zone_id: str,
    service: ZonesService = Depends(get_zones_service)
):
    """Get a specific zone."""
    zone = await service.get_zone(stream_id, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found in stream {stream_id}"
        )
    return zone

@router.put("/{zone_id}", response_model=Zone)
async def update_zone(
    stream_id: str,
    zone_id: str,
    edit_zone: EditZone,
    service: ZonesService = Depends(get_zones_service)
):
    """Update a zone."""
    try:
        zone = await service.update_zone(stream_id, zone_id, edit_zone)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found in stream {stream_id}"
            )
        return zone
    except ValueError as e:
        logger.error(f"Error updating zone: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    stream_id: str,
    zone_id: str,
    service: ZonesService = Depends(get_zones_service)
):
    """Delete a zone."""
    success = await service.delete_zone(stream_id, zone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found in stream {stream_id}"
        )
