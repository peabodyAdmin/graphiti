"""
Episode processor service with telemetry support.
"""

import asyncio
import logging
import traceback
from typing import Any, Dict, Optional

from graphiti_core.graphiti import Graphiti
from telemetry.neo4j_client import TelemetryNeo4jClient

logger = logging.getLogger(__name__)

async def process_episode_queue(
    clients: Graphiti, 
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
            episode_name=episode_data["name"],
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
                    episode_name=episode_data["name"],
                    step_name="ingestion", 
                    status="started"
                )
            
            # Call the appropriate add_episode method based on whether we have bulk data
            if isinstance(episode_data.get("episode_body"), list):
                # This is a bulk operation
                await clients.add_episode_bulk(
                    bulk_episodes=episode_data["episode_body"],
                    group_id=group_id,
                    telemetry_client=telemetry_client
                )
            else:
                # This is a single episode operation
                await clients.add_episode(
                    name=episode_data["name"],
                    episode_body=episode_data["episode_body"],
                    source=episode_data["source"],
                    source_description=episode_data["source_description"],
                    reference_time=episode_data["reference_time"],
                    group_id=group_id,
                    uuid=episode_data["uuid"],
                    entity_types=episode_data.get("entity_types"),
                    update_communities=episode_data.get("update_communities", True),
                    tags=episode_data.get("tags", []),
                    labels=episode_data.get("labels", []),
                    telemetry_client=telemetry_client,
                )
            
            # Record success
            if telemetry_client:
                await telemetry_client.record_processing_step(
                    episode_name=episode_data["name"],
                    step_name="ingestion", 
                    status="success"
                )
                await telemetry_client.record_episode_completion(
                    episode_name=episode_data["name"],
                    episodeElementId=episode_data.get("episodeElementId"),
                    status="completed"
                )
            break
        except (Exception) as e:  # We'll define specific error types in Phase 3
            # Record transient error
            if telemetry_client:
                await telemetry_client.record_error(
                    episode_name=episode_data["name"],
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
                        episode_name=episode_data["name"],
                        status="failed"
                    )
                # Phase 3 will include proper storage of failed episodes
                raise
