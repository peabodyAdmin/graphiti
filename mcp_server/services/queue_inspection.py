"""
Queue inspection service for Graphiti MCP server.
Provides non-intrusive tools to monitor and inspect the episode processing queue.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import queue reference from the main server
# This will be set by the main server during initialization
episode_queues = None
telemetry_client = None

# Add debug logging
logger.setLevel(logging.DEBUG)

# Convert to regular functions instead of static methods for proper MCP tool registration

async def get_queue_stats(group_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics about the queue for a specific group_id.
    If group_id is None, returns stats for all groups.
    
    Returns:
        Dictionary containing queue statistics
    """
    logger.debug(f"get_queue_stats called with group_id={group_id}")
    logger.debug(f"episode_queues initialized: {episode_queues is not None}")
    
    if episode_queues is None:
        logger.error("Queue reference not initialized when get_queue_stats was called")
        return {"error": "Queue reference not initialized"}
    
    result = {}
    
    # If group_id is specified, only get stats for that group
    if group_id:
        if group_id not in episode_queues:
            return {"error": f"No queue found for group_id: {group_id}"}
        
        queue = episode_queues[group_id]
        result[group_id] = {
            "size": queue.qsize(),
            "is_empty": queue.empty()
        }
    else:
        # Get stats for all groups
        for gid, queue in episode_queues.items():
            result[gid] = {
                "size": queue.qsize(),
                "is_empty": queue.empty()
            }
    
    # Add telemetry stats if available
    if telemetry_client:
        # For each group, get stats from telemetry
        for gid in result:
            try:
                # Get count of episodes in different states
                telemetry_stats = await telemetry_client.get_episode_stats(gid)
                if telemetry_stats:
                    result[gid].update(telemetry_stats)
            except Exception as e:
                logger.error(f"Error getting telemetry stats: {e}")
                result[gid]["telemetry_error"] = str(e)
    
    return {"groups": result}


async def get_job_by_index(group_id: str, index: int) -> Dict[str, Any]:
    """Get information about a specific job in the queue by its index.
    
    Args:
        group_id: The group ID to inspect
        index: The index of the job in the queue (0-based)
        
    Returns:
        Dictionary containing job details or error message
    """
    logger.debug(f"get_job_by_index called with group_id={group_id}, index={index}")
    logger.debug(f"episode_queues initialized: {episode_queues is not None}")
    
    if episode_queues is None:
        logger.error("Queue reference not initialized when get_job_by_index was called")
        return {"error": "Queue reference not initialized"}
    
    if group_id not in episode_queues:
        logger.warning(f"No queue found for group_id: {group_id}")
        return {"error": f"No queue found for group_id: {group_id}"}
    
    queue = episode_queues[group_id]
    
    if queue.empty():
        logger.info(f"Queue for group_id {group_id} is empty")
        return {"error": "Queue is empty"}
    
    if index < 0 or index >= queue.qsize():
        logger.warning(f"Invalid index: {index}. Queue size: {queue.qsize()}")
        return {"error": f"Invalid index: {index}. Queue size: {queue.qsize()}"}
        
        # Get a copy of the queue items without removing them
        # This is a bit of a hack since we can't easily access queue items by index
        # We'll create a temporary queue, move all items there while collecting them,
        # then move them back to the original queue
        items = []
        temp_queue = asyncio.Queue()
        
        # Move items to temp queue while collecting them
        while not queue.empty():
            item = await queue.get()
            items.append(item)
            await temp_queue.put(item)
        
        # Move items back to original queue
        while not temp_queue.empty():
            await queue.put(await temp_queue.get())
        
        # Return the requested item
        try:
            job_data = items[index]
            # Remove any sensitive information before returning
            if "api_key" in job_data:
                job_data["api_key"] = "[REDACTED]"
                
            # Telemetry detailed info has been removed
            if telemetry_client and "name" in job_data:
                job_data["telemetry"] = {
                    "note": "Detailed telemetry info has been removed"
                }
                    
            return {"job": job_data}
        except IndexError:
            return {"error": f"Failed to retrieve job at index {index}"}
