"""
Neo4j client for telemetry, bypassing Graphiti but using same connection details.
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase
from neo4j.graph import Node, Relationship

logger = logging.getLogger(__name__)

class TelemetryNeo4jClient:
    """Direct Neo4j client for telemetry, bypassing Graphiti but using same connection details."""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """Initialize the telemetry client with Neo4j connection details."""
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.database = database
    
    async def record_episode_start(self, episode_id: str, original_name: str, group_id: str):
        """Record the start of episode processing.
        
        Args:
            episode_id: Unique identifier for the episode
            original_name: Original name of the episode
            group_id: The client's group_id (used as a reference for client_group_id)
        
        Note: All telemetry is stored under group_id='graphiti_logs' regardless of client group_id
        """
        # Use MERGE instead of CREATE to prevent duplicate records
        query = """
        MERGE (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        ON CREATE SET 
            l.original_name = $original_name, 
            l.client_group_id = $client_group_id, 
            l.status = 'started', 
            l.start_time = datetime(),
            l.attempt_count = 1
        ON MATCH SET
            l.attempt_count = COALESCE(l.attempt_count, 0) + 1,
            l.last_attempt_time = datetime()
        RETURN l
        """
        params = {"episode_id": episode_id, "original_name": original_name, "client_group_id": group_id}
        return await self.run_query(query, params)
    
    async def record_episode_completion(self, episode_id: str, status: str):
        """Record the completion of episode processing.
        
        Args:
            episode_id: Unique identifier for the episode
            status: Status to set ('completed' or 'failed')
        """
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        SET l.status = $status, 
            l.end_time = datetime(),
            l.processing_time_ms = duration.between(l.start_time, datetime()).milliseconds
        RETURN l
        """
        params = {"episode_id": episode_id, "status": status}
        result = await self.run_query(query, params)
        
        if not result:
            logger.warning(f"No episode found with id {episode_id} when trying to record completion")
            
        return result
    
    async def record_processing_step(self, episode_id: str, step_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Record a processing step for an episode.
        
        Args:
            episode_id: Unique identifier for the episode
            step_name: Name of the processing step
            status: Status of the step ('started', 'success', 'error', 'warning')
            data: Optional additional data to store with the step
            
        Returns:
            The result of the query or None if it failed
        """
        logger.info(f"Recording processing step for episode {episode_id}: {step_name} - {status}")
        # First check if the episode exists
        check_episode_query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        RETURN l
        """
        check_result = await self.run_query(check_episode_query, {"episode_id": episode_id})
        
        if not check_result:
            logger.warning(f"Cannot record step {step_name} for episode {episode_id}: episode not found")
            return None
            
        data_str = json.dumps(data) if data else "{}"
        
        # For existing steps with 'started' status, update them instead of creating new ones
        if status != 'started':
            # Try to update existing step first
            update_query = """
            MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name, status: 'started'})
            SET s.status = $status,
                s.end_time = datetime(),
                s.data = $data
            RETURN s
            """
            update_params = {"episode_id": episode_id, "step_name": step_name, "status": status, "data": data_str}
            update_result = await self.run_query(update_query, update_params)
            
            if update_result and len(update_result) > 0:
                logger.debug(f"Updated existing step {step_name} for episode {episode_id}")
                return update_result
        
        # Create new step node
        create_step_query = """
        CREATE (s:ProcessingStep {
            step_name: $step_name,
            start_time: CASE WHEN $status = 'started' THEN datetime() ELSE datetime() END,
            end_time: CASE WHEN $status <> 'started' THEN datetime() ELSE null END,
            status: $status,
            data: $data,
            group_id: 'graphiti_logs'
        })
        RETURN s
        """
        create_params = {"step_name": step_name, "status": status, "data": data_str}
        step_result = await self.run_query(create_step_query, create_params)
        
        if not step_result:
            logger.error(f"Failed to create processing step {step_name} for episode {episode_id}")
            return None
        
        # Extract the node ID from the dictionary result
        step_id = None
        if step_result and len(step_result) > 0 and 's' in step_result[0]:
            node = step_result[0]['s']
            # Try all possible ways to extract the ID
            if isinstance(node, dict):
                # Neo4j 4.0+ uses elementId
                if 'elementId' in node:
                    step_id = node['elementId']
                # Older Neo4j versions use identity
                elif 'identity' in node:
                    step_id = node['identity']
                # Some drivers might use id
                elif 'id' in node:
                    step_id = node['id']
                # Last resort, try to get _id for Neo4j 3.x
                elif '_id' in node:
                    step_id = node['_id']
                # If we have no ID but have element ID as a function
                elif hasattr(node, 'element_id') and callable(getattr(node, 'element_id')):
                    step_id = node.element_id()
            logger.debug(f"Extracted step ID: {step_id} from result: {node}")
        
        if step_id is None:
            logger.error(f"Failed to extract step_id from result: {step_result}")
            return None
            
        # Create relationship to the episode
        relate_query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        MATCH (s:ProcessingStep) WHERE id(s) = $step_id
        CREATE (l)-[r:PROCESSED]->(s)
        RETURN r
        """
        relate_params = {"episode_id": episode_id, "step_id": step_id}
        return await self.run_query(relate_query, relate_params)
    
    async def update_processing_step(self, episode_id: str, step_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Update an existing processing step with new status and data."""
        data_str = json.dumps(data) if data else None
        
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
        SET s.status = $status,
            s.end_time = CASE WHEN $status <> 'started' THEN datetime() ELSE s.end_time END,
            s.data = CASE WHEN $data IS NOT NULL THEN $data ELSE s.data END
        RETURN s
        """
        params = {"episode_id": episode_id, "step_name": step_name, "status": status, "data": data_str}
        return await self.run_query(query, params)
    
    async def record_error(self, episode_id: str, step_name: str, error_type: str, error_message: str, 
                         stack_trace: str, context: Optional[Dict[str, Any]] = None):
        """Record an error that occurred during episode processing.
        
        Args:
            episode_id: Unique identifier for the episode
            step_name: Name of the processing step where the error occurred
            error_type: Type of error (e.g., 'AttributeError')
            error_message: Error message
            stack_trace: Full stack trace
            context: Optional context information about the error
            
        Returns:
            The result of the query or None if it failed
        """
        # First check if the episode exists
        check_episode_query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        RETURN l
        """
        check_result = await self.run_query(check_episode_query, {"episode_id": episode_id})
        
        if not check_result:
            logger.warning(f"Cannot record error for episode {episode_id}: episode not found")
            # Still create the error node, but it won't be linked to an episode
            
        # Check if we need to create the processing step first
        step_exists_query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
        RETURN s
        """
        step_exists = await self.run_query(step_exists_query, {"episode_id": episode_id, "step_name": step_name})
        
        # If step doesn't exist and episode exists, create the step first
        if not step_exists and check_result:
            logger.info(f"Creating missing step {step_name} for error recording")
            await self.record_processing_step(episode_id, step_name, "error", {"auto_created": True})
        
        context_str = json.dumps(context) if context else "{}"
        
        # Create the error node with consistent group_id
        create_error_query = """
        CREATE (e:ProcessingError {
            error_type: $error_type,
            error_message: $error_message,
            stack_trace: $stack_trace,
            context: $context,
            resolution_status: 'unresolved',
            resolution_details: '',
            group_id: 'graphiti_logs',
            created_at: datetime(),
            episode_id: $episode_id
        })
        RETURN e
        """
        error_params = {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "context": context_str,
            "episode_id": episode_id
        }
        error_result = await self.run_query(create_error_query, error_params)
        
        if not error_result:
            logger.error(f"Failed to create error record for {episode_id}")
            return None
        
        # Extract the node ID from the dictionary result
        error_id = None
        if error_result and len(error_result) > 0 and 'e' in error_result[0]:
            # Node ID is stored in elementId property for Neo4j 4.0+
            if isinstance(error_result[0]['e'], dict) and 'elementId' in error_result[0]['e']:
                error_id = error_result[0]['e']['elementId']
            # Fallback to 'identity' property for older Neo4j versions
            elif isinstance(error_result[0]['e'], dict) and 'identity' in error_result[0]['e']:
                error_id = error_result[0]['e']['identity']
        
        if error_id is None:
            logger.error(f"Failed to extract error_id from result: {error_result}")
            return None
        
        # If step exists, create relationship between step and error
        if step_exists or check_result:
            relate_query = """
            MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
            MATCH (e:ProcessingError) WHERE id(e) = $error_id
            MERGE (s)-[r:GENERATED_ERROR {
                affected_entity: $affected_entity,
                error_context: $error_context,
                created_at: datetime()
            }]->(e)
            RETURN r
            """
            relate_params = {
                "episode_id": episode_id,
                "step_name": step_name,
                "error_id": error_id,
                "affected_entity": context.get("affected_entity", "") if context else "",
                "error_context": context_str
            }
            return await self.run_query(relate_query, relate_params)
            
        # If we can't create the relationship, at least return the error node
        return error_result
    
    async def record_retry(self, episode_id: str, error_id: int, retry_attempt: int, retry_strategy: str):
        """Record a retry attempt for an error.
        
        Args:
            episode_id: Unique identifier for the episode
            error_id: ID of the error node
            retry_attempt: Count of retry attempts
            retry_strategy: Description of the retry strategy used
            
        Returns:
            The result of the query or None if it failed
        """
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        MATCH (e:ProcessingError) WHERE id(e) = $error_id
        MERGE (e)-[r:RESOLVED_BY_RETRY {
            retry_attempt: $retry_attempt,
            retry_strategy: $retry_strategy,
            timestamp: datetime()
        }]->(l)
        SET e.resolution_status = 'retry_attempted'
        RETURN r
        """
        params = {
            "episode_id": episode_id,
            "error_id": error_id,
            "retry_attempt": retry_attempt,
            "retry_strategy": retry_strategy
        }
        return await self.run_query(query, params)
        
    async def get_telemetry_stats(self):
        """Get overall telemetry statistics.
        
        Returns statistical information about episodes processing, error rates, etc.
        """
        stats_query = """
        MATCH (log:EpisodeProcessingLog {group_id: 'graphiti_logs'})
        WITH count(log) as total_episodes,
             sum(CASE WHEN log.status = 'completed' THEN 1 ELSE 0 END) as completed,
             sum(CASE WHEN log.status = 'failed' THEN 1 ELSE 0 END) as failed,
             sum(CASE WHEN log.status = 'started' AND log.end_time IS NULL THEN 1 ELSE 0 END) as in_progress,
             avg(CASE WHEN log.processing_time_ms IS NOT NULL THEN log.processing_time_ms ELSE null END) as avg_processing_time_ms
        
        OPTIONAL MATCH (error:ProcessingError {group_id: 'graphiti_logs'})
        WITH total_episodes, completed, failed, in_progress, avg_processing_time_ms,
             count(distinct error) as total_errors
             
        RETURN {
            total_episodes: total_episodes, 
            completed: completed, 
            failed: failed, 
            in_progress: in_progress, 
            avg_processing_time_ms: avg_processing_time_ms,
            total_errors: total_errors,
            success_rate: CASE WHEN total_episodes > 0 THEN toFloat(completed) / toFloat(total_episodes) * 100 ELSE 0 END
        } as stats
        """
        
        result = await self.run_query(stats_query)
        if result and len(result) > 0:
            return result[0]['stats']
        return None
        
    async def clear_telemetry_data(self):
        """Clear all telemetry data from the database.
        
        This should only be used for testing or when requested by an administrator.
        """
        logger.warning("Clearing all telemetry data from the database")
        # Delete all telemetry nodes and relationships
        clear_query = """
        MATCH (n) 
        WHERE n:EpisodeProcessingLog OR n:ProcessingStep OR n:ProcessingError
        DETACH DELETE n
        """
        
        return await self.run_query(clear_query)
    
    async def run_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Run a Cypher query against Neo4j.
        
        Returns the query results as a list of dictionaries, or None if an error occurred.
        Each dictionary contains the variables returned by the query.
        """
        try:
            # Debug log for tracking query execution
            logger.debug(f"Executing Neo4j query: {query[:100]}...")
            logger.debug(f"Query parameters: {params}")
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, params or {})
                data = await result.data()
                # Log the query result for debugging
                if not data:
                    logger.warning(f"Query returned no results: {query[:200]}...")
                    logger.warning(f"Query parameters: {params}")
                return data
        except Exception as e:
            # Use proper logger instead of print
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Query: {query[:200]}...")
            logger.error(f"Params: {params}")
            logger.error(traceback.format_exc())
            return None
    
    async def close(self):
        """Close the Neo4j driver connection."""
        await self.driver.close()
