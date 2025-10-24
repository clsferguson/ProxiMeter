"""REST API endpoints for zone management per stream."""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from shapely.geometry import Polygon
from shapely.errors import WKTReadingError

from ..models.zone import Zone, NewZone, EditZone  # Assume models created
from ..services.zones_service import ZonesService  # Assume service
from ..api.errors import raise_validation_error, ErrorCode

router = APIRouter(prefix="/api/streams/{stream_id}/zones", tags=["zones"])

def get_zones_service():
    return ZonesService()

@router.get("", response_model=List[Zone])
async def list_zones(stream_id: str, service: ZonesService = Depends(get_zones_service)):
    """List zones for a stream."""
    try:
        zones = await service.list_zones(stream_id)
        return zones
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Zone)
async def create_zone(
    stream_id: str,
    new_zone: NewZone,
    service: ZonesService = Depends(get_zones_service)
):
    """Create a new zone for a stream."""
    try:
        # Validate polygon: min 3 points, normalized 0-1
        if len(new_zone.points) < 3:
            raise_validation_error("Polygon must have at least 3 points", {"points": len(new_zone.points)})
        
        # Check bounds
        for p in new_zone.points:
            if not (0 <= p.x <= 1 and 0 <= p.y <= 1):
                raise_validation_error("Points must be normalized (0-1)", {"point": p})
        
        # Validate simple polygon with Shapely
        poly_points = [(p.x, p.y) for p in new_zone.points]
        poly = Polygon(poly_points)
        if not poly.is_valid:
            raise_validation_error("Invalid polygon geometry", {"shapely_error": str(poly.buffer(0))})
        
        zone = await service.create_zone(stream_id, new_zone)
        return zone
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        raise HTTPException(status_code=500, detail="Failed to create zone")

@router.get("/{zone_id}", response_model=Zone)
async def get_zone(stream_id: str, zone_id: str, service: ZonesService = Depends(get_zones_service)):
    """Get a specific zone."""
    try:
        zone = await service.get_zone(stream_id, zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        return zone
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get zone")

@router.put("/{zone_id}", response_model=Zone)
async def update_zone(
    stream_id: str,
    zone_id: str,
    edit_zone: EditZone,
    service: ZonesService = Depends(get_zones_service)
):
    """Update a zone."""
    try:
        if edit_zone.points:
            # Re-validate as in create
            if len(edit_zone.points) < 3:
                raise_validation_error("Polygon must have at least 3 points")
            for p in edit_zone.points:
                if not (0 <= p.x <= 1 and 0 <= p.y <= 1):
                    raise_validation_error("Points must be normalized (0-1)")
            poly_points = [(p.x, p.y) for p in edit_zone.points]
            poly = Polygon(poly_points)
            if not poly.is_valid:
                raise_validation_error("Invalid polygon geometry")
        
        zone = await service.update_zone(stream_id, zone_id, edit_zone)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        return zone
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update zone")

@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(stream_id: str, zone_id: str, service: ZonesService = Depends(get_zones_service)):
    """Delete a zone."""
    try:
        deleted = await service.delete_zone(stream_id, zone_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Zone not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete zone")
