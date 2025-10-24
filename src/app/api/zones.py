"""REST API endpoints for zone management."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import logging

from ..services.zones_service import ZonesService
from ..models.zone import Zone, NewZone, EditZone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["zones"])


def get_zones_service() -> ZonesService:
    """Dependency injection for zones service."""
    return ZonesService()


async def get_stream_zone(
    stream_id: str,
    zone_id: str,
    service: ZonesService
) -> dict:
    """Helper to get zone and raise 404 if not found.
    
    Args:
        stream_id: Stream UUID
        zone_id: Zone UUID
        service: Zones service instance
        
    Returns:
        Zone dictionary
        
    Raises:
        HTTPException 404: Zone not found
    """
    zone = await service.get_zone(stream_id, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found in stream {stream_id}"
        )
    return zone


# ============================================================================
# Zone CRUD Endpoints
# ============================================================================

@router.get("/streams/{stream_id}/zones", response_model=List[Zone])
async def list_zones(
    stream_id: str,
    service: ZonesService = Depends(get_zones_service)
) -> List[dict]:
    """List all detection zones for a stream.
    
    Args:
        stream_id: Stream UUID
        
    Returns:
        List of zones with coordinates and metadata
    """
    try:
        return await service.list_zones(stream_id)
    except Exception as e:
        logger.error(f"Error listing zones for stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list zones"
        )


@router.post("/streams/{stream_id}/zones", response_model=Zone, status_code=status.HTTP_201_CREATED)
async def create_zone(
    stream_id: str,
    new_zone: NewZone,
    service: ZonesService = Depends(get_zones_service)
) -> dict:
    """Create a new detection zone for a stream.
    
    Args:
        stream_id: Stream UUID
        new_zone: Zone configuration with name and polygon coordinates
        
    Returns:
        Created zone with generated UUID
        
    Raises:
        HTTPException 400: Invalid zone configuration or stream not found
        HTTPException 500: Server error
    """
    try:
        zone = await service.create_zone(stream_id, new_zone)
        logger.info(f"Created zone {zone.get('id')} for stream {stream_id}")
        return zone
        
    except ValueError as e:
        logger.warning(f"Invalid zone configuration for stream {stream_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating zone for stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create zone"
        )


@router.get("/streams/{stream_id}/zones/{zone_id}", response_model=Zone)
async def get_zone(
    stream_id: str,
    zone_id: str,
    service: ZonesService = Depends(get_zones_service)
) -> dict:
    """Get a specific detection zone.
    
    Args:
        stream_id: Stream UUID
        zone_id: Zone UUID
        
    Returns:
        Zone with coordinates and metadata
        
    Raises:
        HTTPException 404: Zone not found
    """
    try:
        return await get_stream_zone(stream_id, zone_id, service)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting zone {zone_id} for stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get zone"
        )


@router.put("/streams/{stream_id}/zones/{zone_id}", response_model=Zone)
async def update_zone(
    stream_id: str,
    zone_id: str,
    edit_zone: EditZone,
    service: ZonesService = Depends(get_zones_service)
) -> dict:
    """Update an existing detection zone.
    
    Args:
        stream_id: Stream UUID
        zone_id: Zone UUID
        edit_zone: Updated zone configuration (partial update)
        
    Returns:
        Updated zone
        
    Raises:
        HTTPException 400: Invalid zone configuration
        HTTPException 404: Zone not found
        HTTPException 500: Server error
    """
    try:
        zone = await service.update_zone(stream_id, zone_id, edit_zone)
        
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found in stream {stream_id}"
            )
        
        logger.info(f"Updated zone {zone_id} for stream {stream_id}")
        return zone
        
    except ValueError as e:
        logger.warning(f"Invalid zone update for {zone_id} in stream {stream_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating zone {zone_id} for stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update zone"
        )


@router.delete("/streams/{stream_id}/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    stream_id: str,
    zone_id: str,
    service: ZonesService = Depends(get_zones_service)
) -> None:
    """Delete a detection zone.
    
    Args:
        stream_id: Stream UUID
        zone_id: Zone UUID
        
    Raises:
        HTTPException 404: Zone not found
        HTTPException 500: Server error
    """
    try:
        success = await service.delete_zone(stream_id, zone_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found in stream {stream_id}"
            )
        
        logger.info(f"Deleted zone {zone_id} from stream {stream_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting zone {zone_id} from stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete zone"
        )
