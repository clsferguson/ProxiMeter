"""REST API endpoints for detection zone management.

Detection zones define polygonal regions for person detection scoring.
Each zone has coordinates (polygon vertices) and metadata for YOLO integration.

Logging Strategy:
    DEBUG - Zone lookups, list operations, coordinate validation
    INFO  - Zone lifecycle (create/update/delete), zone count
    WARN  - Invalid configurations, zone not found
    ERROR - Service failures, exceptions

Zone Usage:
    - Define areas of interest for person detection
    - Score detections based on proximity to target point
    - Trigger automations when person enters/exits zone
    - Constitution Principle VII: Real-time scoring
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status, Depends
import logging

from ..services.zones_service import ZonesService
from ..models.zone import Zone, NewZone, EditZone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["zones"])


def get_zones_service() -> ZonesService:
    """Dependency injection for zones service.
    
    Returns:
        ZonesService instance for zone CRUD operations
    """
    logger.debug("Injecting ZonesService")
    return ZonesService()


# ============================================================================
# Zone CRUD Endpoints
# ============================================================================

@router.get("/streams/{stream_id}/zones", response_model=list[Zone])
async def list_zones(
    stream_id: str,
    service: ZonesService = Depends(get_zones_service)
) -> list[dict]:
    """List all detection zones for a stream.
    
    Args:
        stream_id: Stream UUID
        
    Returns:
        List of zones with polygon coordinates and metadata
        
    Logs:
        DEBUG: Zone list queries and counts
        ERROR: List failures
    """
    try:
        logger.debug(f"Listing zones for stream: {stream_id}")
        zones = await service.list_zones(stream_id)
        logger.debug(f"Listed {len(zones)} zone(s) for stream {stream_id}")
        return zones
    except Exception as e:
        logger.error(f"Failed to list zones for {stream_id}: {e}", exc_info=True)
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
    
    Validates polygon coordinates and creates zone with generated UUID.
    
    Args:
        stream_id: Stream UUID
        new_zone: Zone config with name, polygon coordinates, target point
        
    Returns:
        Created zone with generated UUID
        
    Raises:
        HTTPException 400: Invalid polygon or stream not found
        HTTPException 500: Server error
        
    Logs:
        INFO: Zone creation with name
        DEBUG: Coordinate validation
        WARN: Invalid configurations
        ERROR: Creation failures
    """
    try:
        logger.info(f"Creating zone '{new_zone.name}' for stream {stream_id}")
        logger.debug(f"Zone coordinates: {len(new_zone.coordinates)} vertices")
        
        zone = await service.create_zone(stream_id, new_zone)
        logger.info(f"Zone created: {zone.get('name')} ({zone.get('id')})")
        return zone
        
    except ValueError as e:
        logger.warning(f"Invalid zone config for {stream_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create zone for {stream_id}: {e}", exc_info=True)
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
        Zone with polygon coordinates and metadata
        
    Raises:
        HTTPException 404: Zone not found
        
    Logs:
        DEBUG: Zone lookups
        WARN: Zone not found
        ERROR: Get failures
    """
    try:
        logger.debug(f"Getting zone {zone_id} for stream {stream_id}")
        
        zone = await service.get_zone(stream_id, zone_id)
        if not zone:
            logger.warning(f"Zone not found: {zone_id} in stream {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found"
            )
        
        logger.debug(f"Retrieved zone: {zone.get('name', 'Unknown')}")
        return zone
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get zone {zone_id} in {stream_id}: {e}", exc_info=True)
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
    
    Partial update - only provided fields are updated.
    Validates new polygon coordinates if provided.
    
    Args:
        stream_id: Stream UUID
        zone_id: Zone UUID
        edit_zone: Updated zone config (partial)
        
    Returns:
        Updated zone
        
    Raises:
        HTTPException 400: Invalid polygon coordinates
        HTTPException 404: Zone not found
        HTTPException 500: Server error
        
    Logs:
        INFO: Zone updates
        DEBUG: Update details
        WARN: Invalid configs, zone not found
        ERROR: Update failures
    """
    try:
        logger.info(f"Updating zone {zone_id} in stream {stream_id}")
        
        if edit_zone.coordinates:
            logger.debug(f"Updating coordinates: {len(edit_zone.coordinates)} vertices")
        
        zone = await service.update_zone(stream_id, zone_id, edit_zone)
        
        if not zone:
            logger.warning(f"Update failed - zone not found: {zone_id} in {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found"
            )
        
        logger.info(f"Zone updated: {zone_id}")
        return zone
        
    except ValueError as e:
        logger.warning(f"Invalid zone update for {zone_id} in {stream_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update zone {zone_id} in {stream_id}: {e}", exc_info=True)
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
        
    Logs:
        INFO: Zone deletions
        WARN: Zone not found
        ERROR: Delete failures
    """
    try:
        logger.info(f"Deleting zone {zone_id} from stream {stream_id}")
        
        success = await service.delete_zone(stream_id, zone_id)
        
        if not success:
            logger.warning(f"Delete failed - zone not found: {zone_id} in {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found"
            )
        
        logger.info(f"Zone deleted: {zone_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete zone {zone_id} from {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete zone"
        )


logger.debug("Zone management router initialized")
