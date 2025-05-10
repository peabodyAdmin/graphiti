"""
Episode processor service with telemetry support.
"""

import asyncio
import logging
import traceback
from typing import Any, Dict, Optional

from graphiti_core.graphiti_types import GraphitiClients
from mcp_server.telemetry.neo4j_client import TelemetryNeo4jClient

logger = logging.getLogger(__name__)

async def process_episode_queue(
    clients: GraphitiClients, 
    telemetry_client: Optional[TelemetryNeo4jClient], 
    group_id: str, 
    episode_data: Dict[str, Any]
):
    """
    Process an episode with telemetry tracking.
    
    This function handles the processing of an episode, recording telemetry
    at each step and implementing proper error handling with retries.
    
    Args:
        clients: GraphitiClients instance to interact with the knowledge graph
        telemetry_client: TelemetryNeo4jClient for recording telemetry data
        group_id: Group ID for the episode
        episode_data: Episode data to process
    """
    # Record start of processing
    if telemetry_client:
        await telemetry_client.record_episode_start(
            episode_id=episode_data["name"],
            original_name=episode_data["name"],
            group_id=group_id
        )
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Record processing step start
            if telemetry_client:
                await telemetry_client.record_processing_step(
                    episode_id=episode_data["name"],
                    step_name="ingestion", 
                    status="started"
                )
            
            # Call the appropriate add_episode method based on whether we have bulk data
            if isinstance(episode_data.get("episode_body"), list):
                # This is a bulk operation
                await clients.graphiti.add_episode_bulk(
                    bulk_episodes=episode_data["episode_body"],
                    group_id=group_id,
                    telemetry_client=telemetry_client
                )
            else:
                # This is a single episode operation
                await clients.graphiti.add_episode(
                    name=episode_data["name"],
                    episode_body=episode_data["episode_body"],
                    source_description=episode_data.get("source_description", ""),
                    reference_time=episode_data.get("reference_time", None),
                    source=episode_data.get("source", "message"),
                    group_id=group_id,
                    uuid=episode_data.get("uuid", None),
                    update_communities=episode_data.get("update_communities", False),
                    entity_types=episode_data.get("entity_types", None),
                    previous_episode_uuids=episode_data.get("previous_episode_uuids", None),
                    telemetry_client=telemetry_client
                )
            
            # Record success
            if telemetry_client:
                await telemetry_client.record_processing_step(
                    episode_id=episode_data["name"],
                    step_name="ingestion", 
                    status="success"
                )
                await telemetry_client.record_episode_completion(
                    episode_id=episode_data["name"],
                    status="completed"
                )
            break
        except (Exception) as e:  # We'll define specific error types in Phase 3
            # Record transient error
            if telemetry_client:
                await telemetry_client.record_error(
                    episode_id=episode_data["name"],
                    step_name="ingestion",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={"retry_count": retry_count}
                )
            
            retry_count += 1
            await asyncio.sleep(3 ** retry_count)  # Exponential backoff
            
            logger.warning(f"Retrying episode processing (attempt {retry_count}/{max_retries}): {str(e)}")
            
            if retry_count >= max_retries:
                logger.error(f"Failed to process episode after {max_retries} retries")
                if telemetry_client:
                    await telemetry_client.record_episode_completion(
                        episode_id=episode_data["name"],
                        status="failed"
                    )
                # Phase 3 will include proper storage of failed episodes
                raise
