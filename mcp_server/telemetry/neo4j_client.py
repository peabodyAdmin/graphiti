"""
Neo4j client for telemetry, bypassing Graphiti but using same connection details.
"""

import json
import logging
import re
import traceback
from datetime import datetime
import datetime as dt_module  # For timedelta
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase
from neo4j.graph import Node, Relationship

logger = logging.getLogger(__name__)

class TelemetryNeo4jClient:
    """Direct Neo4j client for telemetry, bypassing Graphiti but using same connection details."""
    
    # Constants
    TELEMETRY_GROUP_ID = 'graphiti_logs'
    CONTENT_GROUP_ID = 'graphiti'
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j", group_id: str = None):
        """Initialize the Neo4j Client for telemetry
        
        Args:
            uri: URI for Neo4j server connection
            user: Username for authentication
            password: Password for authentication
            database: Neo4j database name to use
            group_id: Group ID to use for telemetry nodes, or None to be group agnostic
        """
        self.uri = uri
        self.auth = (user, password)  # Convert to tuple for Neo4j driver
        self.database = database
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth)
        self.initialization_verified = False
        
        # Make group_id configurable - this allows for more flexible telemetry queries
        # If None, the client will search across all groups
        self.group_id = group_id
        # Log connection details (without password)
        logger.info(f"Initialized Neo4j telemetry client: URI={uri}, Database={database}")
        

    
    def _get_group_filter(self, include_group_id=True):
        """Get the appropriate group filter based on configured group_id
        
        Args:
            include_group_id: Whether to include group_id in filter
            
        Returns:
            Dict of parameters to include in query params, and string for cypher WHERE clause
        """
        # For telemetry, we always want to use 'graphiti_logs' as the group_id
        if not include_group_id:
            return {}, ""
        else:
            return {"group_id": self.TELEMETRY_GROUP_ID}, f"group_id: '{self.TELEMETRY_GROUP_ID}'"
            
    async def verify_connection(self):
        """Verify that we can connect to the database and write data."""
        logger.info("Testing Neo4j connection and write capabilities...")
        test_id = f"test_{int(datetime.utcnow().timestamp())}"
        test_query = """
        CREATE (t:TelemetryTest {test_id: $test_id, timestamp: datetime()})
        RETURN t
        """
        
        try:
            result = await self.run_query(test_query, {"test_id": test_id})
            if result and len(result) > 0:
                logger.info(f"Successfully wrote test node to Neo4j with ID: {test_id}")
                
                # Clean up test node
                cleanup_query = "MATCH (t:TelemetryTest {test_id: $test_id}) DELETE t"
                await self.run_query(cleanup_query, {"test_id": test_id})
                self.initialization_verified = True
                return True
            else:
                logger.error("Could not verify Neo4j write capability - no results returned")
                return False
        except Exception as e:
            logger.error(f"Failed to verify Neo4j connection: {str(e)}")
            return False

    async def ensure_verified(self):
        """Ensure that the connection has been verified at least once."""
        if not self.initialization_verified:
            await self.verify_connection()
            
    async def record_episode_start(self, episode_name: str, original_name: str, group_id: str):
        """Record the start of episode processing.
        
        Args:
            episode_name: Unique identifier for the episode
            original_name: Original name of the episode
            group_id: The client's group_id (used as a reference for client_group_id)
        
        Note: All telemetry is stored under group_id='graphiti_logs' regardless of client group_id
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        # Use MERGE instead of CREATE to prevent duplicate records
        query = """
        MERGE (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
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
        params = {"episode_name": episode_name, "original_name": original_name, "client_group_id": group_id}
        result = await self.run_query(query, params)
        
        # Create EpisodeTracking node for this processing attempt
        tracking_query = """
        CREATE (t:EpisodeTracking {
            episode_name: $episode_name,
            original_name: $original_name,
            client_group_id: $client_group_id,
            tracking_id: $tracking_id,
            attempt_number: $attempt_number,
            created_at: datetime(),
            status: 'in_progress',
            group_id: 'graphiti_logs'
        })
        WITH t
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
        MERGE (l)-[r:TRACKED_BY]->(t)
        RETURN t
        """
        
        # Generate a unique tracking ID
        import uuid
        tracking_id = f"track_{uuid.uuid4().hex}"
        attempt_number = result[0]['l'].get('attempt_count') if result and len(result) > 0 and 'l' in result[0] else 1
        
        tracking_params = {
            "episode_name": episode_name,
            "original_name": original_name,
            "client_group_id": group_id,
            "tracking_id": tracking_id,
            "attempt_number": attempt_number
        }
        
        try:
            tracking_result = await self.run_query(tracking_query, tracking_params)
            logger.info(f"Created EpisodeTracking node {tracking_id} for episode {episode_name} (attempt {attempt_number})")
        except Exception as e:
            logger.error(f"Failed to create EpisodeTracking node for {episode_name}: {str(e)}")
        
        return result
    
    async def record_episode_completion(self, episode_name: str, status: str, episodeElementId: str = None):
        """Record the completion of episode processing.
        
        Args:
            episode_name: Unique identifier for the episode
            status: Status to set ('completed' or 'failed')
            episodeElementId: Optional canonical episode element ID (set if ingestion succeeded)
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        
        # 1. First update the episode log with completion status and calculate processing time
        query = """
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
        SET l.status = $status, 
            l.end_time = datetime(),
            l.processing_time_ms = duration.between(l.start_time, datetime()).milliseconds
        """
        if episodeElementId:
            query += "    , l.episodeElementId = $episodeElementId\n"
        query += "RETURN l, l.processing_time_ms as processing_time_ms\n"
        params = {"episode_name": episode_name, "status": status}
        if episodeElementId:
            params["episodeElementId"] = episodeElementId
        result = await self.run_query(query, params)
        
        if not result:
            logger.warning(f"No episode found with id {episode_name} when trying to record completion")
            return None
            
        # 2. Create a separate EpisodeTiming node for better analytics
        try:
            processing_time_ms = result[0].get('processing_time_ms')
            timing_query = """
            CREATE (t:EpisodeTiming {
                episode_name: $episode_name,
                processing_time_ms: $processing_time_ms,
                status: $status,
                recorded_at: datetime(),
                group_id: 'graphiti_logs'
            })
            WITH t
            MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
            MERGE (l)-[r:HAS_TIMING]->(t)
            RETURN t
            """
            timing_params = {
                "episode_name": episode_name, 
                "processing_time_ms": processing_time_ms,
                "status": status
            }
            await self.run_query(timing_query, timing_params)
            logger.info(f"Created EpisodeTiming node for {episode_name} with processing time {processing_time_ms}ms")
            
            # 3. Create relationships between steps to show processing sequence
            steps_query = """
            MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})-[:PROCESSED]->(steps:ProcessingStep)
            WITH steps ORDER BY steps.start_time ASC
            WITH collect(steps) as ordered_steps
            UNWIND range(0, size(ordered_steps) - 2) as i
            WITH ordered_steps[i] as current, ordered_steps[i+1] as next
            MERGE (current)-[r:FOLLOWED_BY]->(next)
            RETURN count(r) as relationships_created
            """
            steps_result = await self.run_query(steps_query, {"episode_name": episode_name})
            if steps_result and len(steps_result) > 0 and 'relationships_created' in steps_result[0]:
                logger.info(f"Created {steps_result[0]['relationships_created']} step sequence relationships for {episode_name}")
            
            # 4. Update EpisodeTracking nodes for this episode
            tracking_update_query = """
            MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})-[:TRACKED_BY]->(t:EpisodeTracking)
            WHERE t.status = 'in_progress'
            SET t.status = $status,
                t.completed_at = datetime(),
                t.processing_time_ms = $processing_time_ms
            RETURN t
            """
            tracking_params = {
                "episode_name": episode_name,
                "status": status,
                "processing_time_ms": processing_time_ms
            }
            tracking_update_result = await self.run_query(tracking_update_query, tracking_params)
            logger.info(f"Updated EpisodeTracking for {episode_name} with status {status} and processing time {processing_time_ms}ms")
            
        except Exception as e:
            logger.error(f"Error creating timing analytics for {episode_name}: {str(e)}")
            
        return result
    
    async def create_episode_log(self, episode_name: str, status: str = "in_progress"):
        """Create a new episode log node in the database.
        
        Args:
            episode_name: Unique identifier for the episode
            status: Initial status for the episode log
            
        Returns:
            The result of the query or None if it failed
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        try:
            # Use MERGE instead of CREATE to ensure idempotency
            query = """
            MERGE (l:EpisodeProcessingLog {
                episode_name: $episode_name,
                group_id: 'graphiti_logs'
            })
            ON CREATE SET l.status = $status, 
                         l.created_at = datetime()
            RETURN l
            """
            params = {"episode_name": episode_name, "status": status}
            result = await self.run_query(query, params)
            return result
        except Exception as e:
            logger.error(f"Error creating episode log: {e}")
            return None
    
    async def record_processing_step(self, episode_name: str, step_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Record a processing step for an episode.
        
        Args:
            episode_name: Unique identifier for the episode
            step_name: Name of the processing step
            status: Status of the step ('started', 'success', 'error', 'warning')
            data: Optional additional data to store with the step
            
        Returns:
            The result of the query or None if it failed
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        logger.info(f"Recording processing step for episode {episode_name}: {step_name} - {status}")
        # Ensure the episode exists - create it if it doesn't
        check_episode_query = """
        MERGE (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
        ON CREATE SET l.created_at = datetime(), l.status = 'in_progress'
        RETURN l
        """
        check_result = await self.run_query(check_episode_query, {"episode_name": episode_name})
        
        if not check_result:
            logger.error(f"Failed to ensure episode log exists for {episode_name}")
            return None
            
        data_str = json.dumps(data) if data else "{}"
        
        # For existing steps with 'started' status, update them instead of creating new ones
        if status != 'started':
            # Try to update existing step first
            update_query = """
            MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name, status: 'started'})
            SET s.status = $status,
                s.end_time = datetime(),
                s.data = $data
            RETURN s
            """
            update_params = {"episode_name": episode_name, "step_name": step_name, "status": status, "data": data_str}
            update_result = await self.run_query(update_query, update_params)
            
            if update_result and len(update_result) > 0:
                logger.debug(f"Updated existing step {step_name} for episode {episode_name}")
                return update_result
        
        # Generate a unique step_id that we can use for matching later
        import time
        import uuid
        # Make sure the step_id is guaranteed unique by using UUID
        unique_step_id = f"{step_name}_{uuid.uuid4().hex}"
        
        # Create new step node with explicit step_id property
        create_step_query = """
        CREATE (s:ProcessingStep {
            step_id: $step_id,
            step_name: $step_name,
            start_time: CASE WHEN $status = 'started' THEN datetime() ELSE datetime() END,
            end_time: CASE WHEN $status <> 'started' THEN datetime() ELSE null END,
            status: $status,
            data: $data,
            group_id: 'graphiti_logs'
        })
        RETURN s
        """
        create_params = {"step_id": unique_step_id, "step_name": step_name, "status": status, "data": data_str}
        step_result = await self.run_query(create_step_query, create_params)
        
        if not step_result:
            logger.error(f"Failed to create processing step {step_name} for episode {episode_name}")
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
                # Generate synthetic ID if all else fails
                else:
                    # Use a combination of step_name and timestamp as a synthetic ID
                    # This will at least let us create relationships even if we can't get the true Neo4j ID
                    if 'step_name' in node and 'start_time' in node:
                        step_id = f"{node['step_name']}_{hash(str(node['start_time']))}"
                        logger.info(f"Using synthetic ID for step: {step_id}")
            logger.debug(f"Extracted step ID: {step_id} from result: {node}")
        
        if step_id is None:
            logger.warning(f"Failed to extract step_id from result: {step_result}")
            # Instead of returning None, let's continue with a synthetic ID based on timestamp
            import time
            step_id = f"synthetic_{time.time()}"
            logger.info(f"Using fallback synthetic ID: {step_id}")
            # Return empty result but don't fail completely
            return []
            
        # Update the step with a unique step_id property we can use for matching
        update_step_query = """
        MATCH (s:ProcessingStep) WHERE elementId(s) = $element_id OR s.step_name = $step_name
        SET s.step_id = $step_id
        RETURN s
        """
        # Try to use elementId if available, otherwise fall back to step_id
        element_id = step_id if isinstance(step_id, int) else None
        update_params = {"element_id": element_id, "step_name": step_name, "step_id": step_id}
        await self.run_query(update_step_query, update_params)
        
        # Create relationship to the episode using the step_id property
        relate_query = """
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
        MATCH (s:ProcessingStep {step_id: $step_id})
        MERGE (l)-[r:PROCESSED]->(s)
        RETURN r
        """
        relate_params = {"episode_name": episode_name, "step_id": step_id}
        return await self.run_query(relate_query, relate_params)
    
    async def update_processing_step(self, episode_name: str, step_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Update an existing processing step with new status and data."""
        data_str = json.dumps(data) if data else None
        
        query = """
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
        SET s.status = $status,
            s.end_time = CASE WHEN $status <> 'started' THEN datetime() ELSE s.end_time END,
            s.data = CASE WHEN $data IS NOT NULL THEN $data ELSE s.data END
        RETURN s
        """
        params = {"episode_name": episode_name, "step_name": step_name, "status": status, "data": data_str}
        return await self.run_query(query, params)
    
    async def record_error(self, episode_name: str, step_name: str, error_type: str, error_message: str, 
                         stack_trace: str, context: Optional[Dict[str, Any]] = None):
        """Record an error that occurred during episode processing.
        
        Args:
            episode_name: Unique identifier for the episode
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
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
        RETURN l
        """
        check_result = await self.run_query(check_episode_query, {"episode_name": episode_name})
        
        if not check_result:
            logger.warning(f"Cannot record error for episode {episode_name}: episode not found")
            # Still create the error node, but it won't be linked to an episode
            
        # Check if we need to create the processing step first
        step_exists_query = """
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
        RETURN s
        """
        step_exists = await self.run_query(step_exists_query, {"episode_name": episode_name, "step_name": step_name})
        
        # If step doesn't exist and episode exists, create the step first
        if not step_exists and check_result:
            logger.info(f"Creating missing step {step_name} for error recording")
            await self.record_processing_step(episode_name, step_name, "error", {"auto_created": True})
        
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
            episode_name: $episode_name
        })
        RETURN e
        """
        error_params = {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "context": context_str,
            "episode_name": episode_name
        }
        error_result = await self.run_query(create_error_query, error_params)
        
        if not error_result:
            logger.error(f"Failed to create error record for {episode_name}")
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
            MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
            MATCH (e:ProcessingError {error_id: $error_id, group_id: 'graphiti_logs'})
            MERGE (s)-[r:GENERATED_ERROR {
                affected_entity: $affected_entity,
                error_context: $error_context,
                created_at: datetime()
            }]->(e)
            RETURN r
            """
            relate_params = {
                "episode_name": episode_name,
                "step_name": step_name,
                "error_id": error_id,
                "affected_entity": context.get("affected_entity", "") if context else "",
                "error_context": context_str
            }
            return await self.run_query(relate_query, relate_params)
            
        # If we can't create the relationship, at least return the error node
        return error_result
    
    async def record_retry(self, episode_name: str, error_id: int, retry_attempt: int, retry_strategy: str):
        """Record a retry attempt for an error.
        
        Args:
            episode_name: Unique identifier for the episode
            error_id: ID of the error node
            retry_attempt: Count of retry attempts
            retry_strategy: Description of the retry strategy used
            
        Returns:
            The result of the query or None if it failed
        """
        query = """
        MATCH (l:EpisodeProcessingLog {episode_name: $episode_name, group_id: 'graphiti_logs'})
        MATCH (e:ProcessingError {error_id: $error_id, group_id: 'graphiti_logs'})
        MERGE (e)-[r:RESOLVED_BY_RETRY {
            retry_attempt: $retry_attempt,
            retry_strategy: $retry_strategy,
            timestamp: datetime()
        }]->(l)
        SET e.resolution_status = 'retry_attempted'
        RETURN r
        """
        params = {
            "episode_name": episode_name,
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
        # Critical debugging - print the exact query and params to help identify issues
        # Truncate long queries for readability
        query_excerpt = query[:200] + "..." if len(query) > 200 else query
        logger.info(f"\nEXECUTING QUERY:\n{query_excerpt}\nPARAMS: {params}\n")
        try:
            # Debug log for tracking query execution
            logger.debug(f"Executing Neo4j query: {query[:100]}...")
            logger.debug(f"Query parameters: {params}")
            
            async with self.driver.session(database=self.database) as session:
                # Use explicit transaction for proper commit/rollback handling
                is_write_query = any(keyword in query.upper() for keyword in ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'FOREACH'])
                
                # This is the key change: ensure all queries use the same transaction pattern
                # for maximum reliability
                async def run_tx(tx):
                    try:
                        tx_type = "write" if is_write_query else "read"
                        logger.info(f"Executing {tx_type} transaction: {query[:100]}...")
                        
                        # Run the query
                        result = await tx.run(query, params or {})
                        
                        # Must collect data before transaction closes
                        records = await result.data()
                        
                        # Get summary after collecting records
                        summary = await result.consume()
                        logger.info(f"Transaction summary - counters: {summary.counters}")
                        
                        # Log the specific changes made
                        if is_write_query and summary.counters:
                            changes = vars(summary.counters)
                            changes_str = ', '.join([f"{k}: {v}" for k, v in changes.items() if v > 0])
                            logger.info(f"Database changes: {changes_str}")
                        
                        return records
                    except Exception as inner_e:
                        logger.error(f"Error in {tx_type} transaction: {str(inner_e)}")
                        logger.error(f"Query: {query}")
                        logger.error(f"Params: {params}")
                        raise  # Re-raise to ensure transaction is rolled back
                
                # Execute appropriate transaction type but use same handler
                if is_write_query:
                    logger.info("Starting write transaction execution")
                    data = await session.execute_write(run_tx)
                    logger.info("Write transaction committed successfully")
                else:
                    logger.info(f"Starting read transaction on database: {self.database}")
                    data = await session.execute_read(run_tx)
                    logger.info("Read transaction completed successfully")
                
                # Log if no results found
                if not data:
                    logger.warning(f"Query returned no results: {query[:200]}...")
                    logger.warning(f"Query parameters: {params}")
                
                # Success! Return the data
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
    
    async def get_episode_stats(self, group_id: str) -> Dict[str, Any]:
        """
        Get statistics about episodes for a specific client group_id.
        
        Args:
            group_id: The client group_id to get stats for
            
        Returns:
            Dictionary with statistics
        """
        query = """
        MATCH (l:EpisodeProcessingLog {client_group_id: $group_id})
        RETURN 
            count(l) as total,
            sum(CASE WHEN l.status = 'started' THEN 1 ELSE 0 END) as in_progress,
            sum(CASE WHEN l.status = 'completed' THEN 1 ELSE 0 END) as completed,
            sum(CASE WHEN l.status = 'failed' THEN 1 ELSE 0 END) as failed
        """
        params = {"group_id": group_id}
        
        result = await self.run_query(query, params)
        if result and len(result) > 0:
            return {
                "total_episodes": result[0]['total'],
                "in_progress": result[0]['in_progress'],
                "completed": result[0]['completed'],
                "failed": result[0]['failed']
            }
        return {}
    
    async def get_episode_info(self, episode_nameentifier: str) -> Dict[str, Any]:
        """Get detailed information about an episode, including processing steps and errors.
        
        Args:
            episode_nameentifier: Either the episode_name property value OR a Neo4j internal ID 
                              in the format "1105c001-9aca-44df-b787-08a8d10a5d70"
            
        Returns:
            Dictionary with episode information
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        
        # Determine if this is likely a Neo4j elementId (UUID format) or an episode_name property
        is_neo4j_id = bool(re.match(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', episode_nameentifier))
        
        logger.info(f"Looking up episode with {'Neo4j ID' if is_neo4j_id else 'episode_name'}: {episode_nameentifier}")
        
        # Construct the appropriate query based on identifier type
        if is_neo4j_id:
            # Handle Neo4j internal ID lookup - extract the UUID portion
            uuid_parts = episode_nameentifier.split(':')
            if len(uuid_parts) > 1:
                # If format is like "4:1105c001-9aca-44df-b787-08a8d10a5d70:121", extract the UUID
                uuid = uuid_parts[1]
            else:
                # If already just a UUID
                uuid = episode_nameentifier
                
            query = f"""
            MATCH (l) WHERE id(l) = $node_id AND l.group_id = '{self.TELEMETRY_GROUP_ID}'
            RETURN l as episode
            """
            params = {"node_id": int(uuid_parts[2]) if len(uuid_parts) > 2 else None}  # Convert ID part to integer
            
            logger.info(f"Querying with Neo4j ID parameters: {params}")
        else:
            # Regular episode_name property lookup
            query = f"""
            MATCH (l:EpisodeProcessingLog {{episode_name: $episode_name, group_id: '{self.TELEMETRY_GROUP_ID}'}}) 
            OPTIONAL MATCH (l)-[:TRACKED_BY]->(t:EpisodeTracking)
            OPTIONAL MATCH (l)-[:HAS_TIMING]->(timing:EpisodeTiming)
            OPTIONAL MATCH (l)-[:PROCESSED]->(s:ProcessingStep)
            RETURN l as episode, 
                   collect(distinct t) as tracking,
                   collect(distinct timing) as timing_data,
                   collect(distinct s) as steps_data
            """
            params = {"episode_name": episode_nameentifier}
        
        result = await self.run_query(query, params)
        
        # If the primary lookup failed, try alternative approaches
        if not result or len(result) == 0:
            logger.warning(f"Primary lookup failed for {episode_nameentifier}, trying alternatives")
            
            # Try a more generic lookup approach
            fallback_query = f"""
            MATCH (l) 
            WHERE l.group_id = '{self.TELEMETRY_GROUP_ID}' AND
                  (l.episode_name = $id OR 
                   l.original_name = $id OR
                   toString(id(l)) CONTAINS $id_fragment)
            RETURN l as episode LIMIT 1
            """
            
            # Extract a fragment to use for partial matching on Neo4j IDs
            id_fragment = episode_nameentifier.split(':')[1] if ':' in episode_nameentifier else episode_nameentifier
            id_fragment = id_fragment[:8]  # Use first portion for matching
            
            fallback_params = {"id": episode_nameentifier, "id_fragment": id_fragment}
            result = await self.run_query(fallback_query, fallback_params)
            
            if not result or len(result) == 0:
                logger.error(f"All lookup attempts failed for {episode_nameentifier}")
                return {}
        
        episode_data = result[0].get('episode', {})
        logger.info(f"Found episode: {episode_data}")
        # Process tracking data
        tracking_data = [dict(t) for t in result[0]['tracking'] if t is not None]
        
        # Process timing data
        timing_data = [dict(t) for t in result[0]['timing_data'] if t is not None]
        
        # Process steps data
        steps_data = [dict(s) for s in result[0]['steps_data'] if s is not None] if 'steps_data' in result[0] else []
        
        # Format datetime objects to strings in all data structures
        for key in episode_data:
            if isinstance(episode_data[key], datetime):
                episode_data[key] = episode_data[key].isoformat()
                
        # Format datetime objects in steps data
        for step in steps_data:
            for key in step:
                if isinstance(step[key], datetime):
                    step[key] = step[key].isoformat()
                    
        # Format datetime objects in tracking data
        for track in tracking_data:
            for key in track:
                if isinstance(track[key], datetime):
                    track[key] = track[key].isoformat()
                    
        # Format datetime objects in timing data
        for timing in timing_data:
            for key in timing:
                if isinstance(timing[key], datetime):
                    timing[key] = timing[key].isoformat()
                
        # Add processing timeline
        timeline = []
        for step in steps_data:
            timeline.append({
                "step_name": step.get("step_name", "Unknown step"),
                "status": step.get("status", "unknown"),
                "timestamp": step.get("start_time", ""),
                "duration_ms": step.get("duration_ms", 0),
                "message": self._get_step_message(step)
            })
            
        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        # Add processing outcome summary
        success = episode_data.get("status") == "completed"
        processing_time = episode_data.get("processing_time_ms", 0)
        
        outcome_summary = {
            "success": success,
            "processing_time_ms": processing_time,
            "total_steps": len(steps_data),
            "error_count": sum(1 for step in steps_data if step.get("status") == "error"),
            "completion_time": episode_data.get("end_time", ""),
            "attempt_count": episode_data.get("attempt_count", 1)
        }
        
        # Return enhanced data
        return {
            "episode": episode_data,
            "steps": steps_data,
            "tracking": tracking_data,
            "timing": timing_data,
            "timeline": timeline,
            "outcome_summary": outcome_summary
        }
        
    def _get_step_message(self, step) -> str:
        """Generate a human-readable message about a processing step.
        
        Args:
            step: Dictionary containing step data
            
        Returns:
            A string message describing the step
        """
        status = step.get("status", "unknown")
        step_name = step.get("step_name", "Unknown step")
        
        if status == "success":
            return f"Successfully completed {step_name}"
        elif status == "error":
            error_type = step.get("data", {}).get("error_type", "Unknown error")
            error_message = step.get("data", {}).get("error_message", "No details available")
            return f"Error in {step_name}: {error_type} - {error_message}"
        elif status == "started":
            return f"Started {step_name}"
        elif status == "warning":
            message = step.get("data", {}).get("message", "No details available")
            return f"Warning in {step_name}: {message}"
        else:
            return f"{step_name} status: {status}"
        
    async def find_failed_episodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Find episodes that failed processing.
        
        Args:
            limit: Maximum number of failed episodes to return
            
        Returns:
            List of dictionaries with episode information
        """
        query = f"""
        MATCH (l:EpisodeProcessingLog {{status: 'failed', group_id: '{self.TELEMETRY_GROUP_ID}'}})
        OPTIONAL MATCH (l)-[:PROCESSED]->(:ProcessingStep)-[:GENERATED_ERROR]->(e:ProcessingError)
        RETURN DISTINCT l.episode_name as episode_name, l.original_name as name, 
               l.processing_time_ms as processing_time_ms, count(e) as error_count
        ORDER BY l.start_time DESC
        LIMIT $limit
        """
        
        params = {"limit": limit}
        result = await self.run_query(query, params)
        
        if not result:
            return []
            
        return [dict(r) for r in result]
    
    async def find_episode_by_name_or_id(self, search_term: str, limit: int = 5, client_group_id: str = None):
        """Find telemetry for episodes using a name, title, or ID string.
        
        This method supports partial matching and returns multiple results when appropriate.
        
        Args:
            search_term: Any identifier string - could be an episode name, title, or UUID
            limit: Maximum number of matching episodes to return
            client_group_id: Optional client group_id to filter telemetry records
            
        Returns:
            List of dictionaries with telemetry information 
        """
        logger.info(f"Searching for telemetry with term: '{search_term}', client_group_id: {client_group_id}")
        
        # More comprehensive diagnostic query to check exactly what's in the database
        diagnostic_query = f"""
        MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}}) 
        RETURN l as full_node, l.episode_name as episode_name, l.original_name as original_name, 
               l.status as status, l.client_group_id as client_group_id,
               l.start_time as start_time, l.end_time as end_time,
               labels(l) as labels
        LIMIT 10
        """
        
        # Run diagnostic query to see what's in the database
        diagnostic_result = await self.run_query(diagnostic_query)
        if diagnostic_result:
            logger.info(f"Sample telemetry records found in database: {diagnostic_result}")
            # Explicitly log the properties of each node for easier debugging
            for i, record in enumerate(diagnostic_result):
                if 'full_node' in record:
                    node_props = record['full_node']
                    logger.info(f"Record {i+1} properties: {node_props}")
        else:
            logger.warning("No telemetry records found in database during diagnostic check")
            
        # Also try a simpler query to check if node structure might be different
        simple_check = f"""
        MATCH (l) WHERE l.group_id = '{self.TELEMETRY_GROUP_ID}'
        RETURN count(l) as count, collect(distinct labels(l)) as node_types
        """
        simple_result = await self.run_query(simple_check)
        if simple_result:
            logger.info(f"Database overview: {simple_result}")
        
        # Build filter clause based on client_group_id
        client_filter = ""
        if client_group_id:
            client_filter = " AND l.client_group_id = $client_group_id"
        
        # Enhanced query with more flexible matching
        query = f"""
        // Exact match (highest priority)
        MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}}) 
        WHERE (l.episode_name = $search_term OR l.original_name = $search_term){client_filter}
        RETURN l as log, 3 as score
        
        UNION
        
        // String contains match (medium priority)
        MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}})  
        WHERE (l.episode_name CONTAINS $search_term OR l.original_name CONTAINS $search_term)
        AND NOT (l.episode_name = $search_term OR l.original_name = $search_term){client_filter}
        RETURN l as log, 2 as score
        
        UNION
        
        // Case-insensitive match (lower priority)
        MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}})  
        WHERE (toLower(l.episode_name) CONTAINS toLower($search_term) OR toLower(l.original_name) CONTAINS toLower($search_term))
        AND NOT (l.episode_name CONTAINS $search_term OR l.original_name CONTAINS $search_term){client_filter}
        RETURN l as log, 1 as score
        
        UNION
        
        // Word boundary match for multi-word titles
        MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}})  
        WHERE ANY(word IN split(l.episode_name, ' ') WHERE word = $search_term)
        OR ANY(word IN split(l.original_name, ' ') WHERE word = $search_term){client_filter}
        AND NOT (toLower(l.episode_name) CONTAINS toLower($search_term) OR toLower(l.original_name) CONTAINS toLower($search_term))
        RETURN l as log, 0.5 as score
        
        ORDER BY score DESC, l.start_time DESC
        LIMIT $limit
        """
        
        params = {"search_term": search_term, "limit": limit}
        if client_group_id:
            params["client_group_id"] = client_group_id
        
        logger.info(f"Executing telemetry search with query params: {params}")
        result = await self.run_query(query, params)
        
        if not result:
            logger.warning(f"No results found for search term: '{search_term}'")
            # Try direct queries with different approaches for diagnosis
            direct_queries = [
                # Case-insensitive search with CONTAINS
                f"""MATCH (l) WHERE l.group_id = '{self.TELEMETRY_GROUP_ID}' 
                    AND (toLower(toString(l.episode_name)) CONTAINS toLower('forgotten') 
                    OR toLower(toString(l.original_name)) CONTAINS toLower('forgotten'))
                RETURN l""",
                # Look for exact matches of the example we know exists
                """MATCH (l) WHERE l.episode_name = 'Novel Story: The Forgotten Atlas' 
                   RETURN l""",
                # Try matching any node with properties that might contain our search term
                """MATCH (l) 
                   WHERE ANY(prop IN keys(l) WHERE toLower(toString(l[prop])) CONTAINS toLower('forgotten'))
                   RETURN l LIMIT 5"""
            ]
            
            # Try each query to see if any find the record
            for i, query in enumerate(direct_queries):
                logger.info(f"Trying diagnostic query approach {i+1}")
                direct_result = await self.run_query(query)
                if direct_result:
                    logger.info(f"Diagnostic query {i+1} found records: {direct_result}")
                    # If we found something, use this approach to actually find the user's record
                    if i == 0:
                        # Case-insensitive CONTAINS was successful
                        recovery_query = f"""MATCH (l) WHERE l.group_id = '{self.TELEMETRY_GROUP_ID}' 
                            AND (toLower(toString(l.episode_name)) CONTAINS toLower($search_term) 
                            OR toLower(toString(l.original_name)) CONTAINS toLower($search_term))
                        RETURN l as log, 2 as score"""
                        recovery_result = await self.run_query(recovery_query, {"search_term": search_term})
                        if recovery_result:
                            logger.info(f"Recovery search succeeded! Found {len(recovery_result)} results")
                            result = recovery_result
                    break
            return []
        
        logger.info(f"Found {len(result)} telemetry matches for '{search_term}'")
        
        # Get detailed info for each match
        matches = []
        for match in result:
            if not match.get('log') or not match['log'].get('episode_name'):
                logger.warning(f"Invalid match result missing log or episode_name: {match}")
                continue
            
            episode_name = match['log']['episode_name']
            logger.info(f"Getting detailed info for episode: {episode_name}")
            detailed_info = await self.get_episode_info(episode_name)
            
            if detailed_info:
                # Add score and relevance info
                if 'episode' in detailed_info:
                    detailed_info['episode']['match_score'] = match['score']
                    if match['score'] == 3:
                        relevance = 'Exact match'
                    elif match['score'] == 2:
                        relevance = 'Partial match'
                    elif match['score'] == 1:
                        relevance = 'Case-insensitive match'
                    else:
                        relevance = 'Word match'
                    detailed_info['episode']['match_relevance'] = relevance
                matches.append(detailed_info)
            else:
                logger.warning(f"Failed to get detailed info for episode: {episode_name}")
        
        logger.info(f"Returning {len(matches)} detailed matches for search term: '{search_term}'")
        return matches
    
    async def find_telemetry_for_content_uuid(self, content_uuid: str) -> Dict[str, Any]:
        """Find telemetry information for a content UUID from the graphiti database.
        
        This method bridges the gap between content nodes (which use UUIDs) and telemetry nodes
        (which typically use episode titles or other identifiers).
        
        Args:
            content_uuid: UUID of the content node in the graphiti database
            
        Returns:
            Dictionary with telemetry information or empty dict if not found
        """
        # First attempt to find any metadata relationship from the content node to telemetry
        query = f"""
        MATCH (c {{uuid: $content_uuid, group_id: '{self.CONTENT_GROUP_ID}'}})
        OPTIONAL MATCH (c)-[:HAS_METADATA]->(m)
        RETURN c.title as title, c.name as name, c.original_title as original_title,
               m.episode_name as episode_name, m.telemetry_id as telemetry_id
        """
        params = {"content_uuid": content_uuid}
        
        result = await self.run_query(query, params)
        if not result or len(result) == 0:
            # If no direct link found, try matching by any known identifiers
            logger.info(f"No direct telemetry link found for content UUID {content_uuid}, trying to match by title")
            return await self._find_telemetry_by_content_attributes(content_uuid)
            
        # If we have a direct telemetry ID, use it
        if result[0].get('telemetry_id'):
            return await self.get_episode_info(result[0]['telemetry_id'])
            
        # Try episode_name next
        if result[0].get('episode_name'):
            return await self.get_episode_info(result[0]['episode_name'])
        
        # Fall back to title-based search
        for field in ['title', 'name', 'original_title']:
            if result[0].get(field):
                telemetry = await self.get_episode_info(result[0][field])
                if telemetry and telemetry.get('episode'):
                    return telemetry
                    
        # If all else fails, try a fuzzy match
        return await self._find_telemetry_by_content_attributes(content_uuid)
        
    async def lookup_telemetry_for_content_uuid(self, content_uuid: str) -> Dict[str, Any]:
        """Find telemetry information for a content node by its UUID.
        
        This is a better bridge between the content system and telemetry system than the existing functions.
        It first looks at the content node's creation time and name, then finds matching telemetry records.
        
        Args:
            content_uuid: UUID of a content node (e.g., "5ae89d70-6fe4-4140-8fc0-c52ff8dafb8c")
            
        Returns:
            Dictionary with telemetry information or empty dict if not found
        """
        logger.info(f"Looking up telemetry for content UUID: {content_uuid}")
        
        # First get basic info about the content node
        content_query = f"""
        MATCH (c)
        WHERE c.uuid = $content_uuid 
        RETURN c.name as name, c.created_at as created_at, labels(c) as labels,
               c.source as source, c.group_id as group_id
        """
        
        content_result = await self.run_query(content_query, {"content_uuid": content_uuid})
        
        if not content_result or len(content_result) == 0:
            logger.warning(f"No content found with UUID: {content_uuid}")
            return {"error": f"No content found with UUID: {content_uuid}"}
        
        content_info = content_result[0]
        logger.info(f"Found content: {content_info}")
        
        # Use the content creation time to find matching telemetry records
        # (telemetry records should exist before the content was created)
        created_at = content_info.get('created_at')
        content_name = content_info.get('name')
        
        # Format timestamps appropriately
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
            created_before_str = (created_at - dt_module.timedelta(minutes=10)).isoformat()
        else:
            # If it's already a string
            created_at_str = created_at
            created_before_str = None
        
        # Get all telemetry logs that match this content by name and timing
        telemetry_query = f"""
        MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}}) 
        WHERE (l.original_name = $content_name OR l.episode_name = $content_name)
        AND l.status = 'completed'
        RETURN l, id(l) as telemetry_id_number
        """
        
        telemetry_result = await self.run_query(telemetry_query, {"content_name": content_name})
        
        if not telemetry_result or len(telemetry_result) == 0:
            logger.warning(f"No telemetry records found for content name: {content_name}")
            # Try a more flexible approach
            fuzzy_query = f"""
            MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}}) 
            WHERE toLower(l.original_name) CONTAINS toLower($name_fragment) 
            OR toLower(l.episode_name) CONTAINS toLower($name_fragment)
            RETURN l, id(l) as telemetry_id_number
            ORDER BY l.start_time DESC
            LIMIT 5
            """
            
            # Get meaningful fragments from the name
            name_words = content_name.split()
            name_fragment = name_words[0] if len(name_words) > 0 else content_name
            if len(name_words) > 1:
                name_fragment += " " + name_words[1]
                
            fuzzy_result = await self.run_query(fuzzy_query, {"name_fragment": name_fragment})
            if not fuzzy_result or len(fuzzy_result) == 0:
                return {"error": f"No telemetry found for content: {content_name}"}
                
            telemetry_result = fuzzy_result
            logger.info(f"Found {len(telemetry_result)} potential telemetry records using fuzzy matching")
        
        # Format the results
        matches = []
        for record in telemetry_result:
            telemetry_node = record.get('l', {})
            telemetry_id = record.get('telemetry_id_number')
            
            episode_info = {"episode": {}}
            # Convert node to dict and handle datetime objects
            for key, value in telemetry_node.items():
                if isinstance(value, datetime):
                    episode_info["episode"][key] = value.isoformat()
                else:
                    episode_info["episode"][key] = value
            
            # Add the Neo4j ID for reference
            episode_info["episode"]["telemetry_node_id"] = telemetry_id
            episode_info["match_confidence"] = "high" if telemetry_node.get('original_name') == content_name else "medium"
            
            # Get detailed processing information
            detailed_info = await self.get_episode_info(telemetry_node.get('episode_name'))
            if detailed_info:
                episode_info.update(detailed_info)
                
            matches.append(episode_info)
        
        return {
            "content_info": content_info,
            "telemetry_matches": matches,
            "matches_found": len(matches)
        }
        
    async def find_related_content(self, episode_name: str, content_group_id: str = None):
        """Find content nodes that were created from this telemetry episode.
        
        Args:
            episode_name: ID of the telemetry episode
            content_group_id: Optional content group_id to search within. If not provided, 
                          will use the client_group_id from the telemetry record.
            
        Returns:
            Dictionary with content information or empty dict if not found
        """
        # First get the telemetry log to get client_group_id
        query = f"""
        MATCH (l:EpisodeProcessingLog {{episode_name: $episode_name, group_id: '{self.TELEMETRY_GROUP_ID}'}})  
        RETURN l.client_group_id as client_group_id, l.original_name as original_name, 
               l.status as status, l.start_time as start_time
        """
        
        params = {"episode_name": episode_name}
        result = await self.run_query(query, params)
        
        if not result or len(result) == 0:
            return {}
            
        # If episode failed, no content would be created
        if result[0]['status'] == 'failed':
            return {
                "content_found": False,
                "reason": "Episode processing failed, no content created",
                "telemetry_status": result[0]['status']
            }
            
        # Use provided content_group_id or fall back to client_group_id from telemetry
        target_group_id = content_group_id or result[0]['client_group_id']
        original_name = result[0]['original_name']
        start_time = result[0]['start_time']
        
        # Format start_time to ISO format if it's a datetime
        if isinstance(start_time, datetime):
            start_time_str = start_time.isoformat()
        else:
            start_time_str = start_time
        
        # Build group filter based on content_group_id
        group_filter = ""
        if target_group_id:
            group_filter = "group_id: $target_group_id"
        
        content_query = f"""
        MATCH (c {{{group_filter}}})
        WHERE c.name = $original_name AND c.created_at >= $start_time
        RETURN c.uuid as uuid, c.name as name, c.group_id as group_id, labels(c) as labels,
               c.created_at as created_at, c.valid_at as valid_at
        """
        
        content_params = {
            "original_name": original_name,
            "start_time": start_time_str
        }
        if target_group_id:
            content_params["target_group_id"] = target_group_id
        
        content_result = await self.run_query(content_query, content_params)
        
        if not content_result or len(content_result) == 0:
            # Try a more flexible search if exact match fails
            fuzzy_content_query = f"""
            MATCH (c {{{group_filter}}})
            WHERE (c.name CONTAINS $name_fragment OR c.title CONTAINS $name_fragment)
            AND c.created_at >= $start_time
            RETURN c.uuid as uuid, c.name as name, c.group_id as group_id, labels(c) as labels,
                   c.created_at as created_at, c.valid_at as valid_at
            """
            
            # Extract a meaningful fragment from the original name
            name_words = original_name.split()
            name_fragment = name_words[0] if len(name_words) > 0 else original_name
            if len(name_words) > 1:
                name_fragment += " " + name_words[1]
                
            fuzzy_params = {
                "name_fragment": name_fragment,
                "start_time": start_time_str
            }
            if target_group_id:
                fuzzy_params["target_group_id"] = target_group_id
            
            content_result = await self.run_query(fuzzy_content_query, fuzzy_params)
        
        if not content_result or len(content_result) == 0:
            return {
                "content_found": False,
                "reason": "No matching content found despite successful processing",
                "telemetry_status": result[0]['status'],
                "search_parameters": {
                    "group_id": target_group_id,
                    "original_name": original_name,
                    "start_time": start_time_str
                }
            }
            
        # Format the results
        content_nodes = []
        for node in content_result:
            formatted_node = dict(node)
            # Convert datetime objects to strings
            for key in formatted_node:
                if isinstance(formatted_node[key], datetime):
                    formatted_node[key] = formatted_node[key].isoformat()
            content_nodes.append(formatted_node)
            
        return {
            "content_found": True,
            "content_nodes": content_nodes,
            "telemetry_status": result[0]['status']
        }
        
    async def _find_telemetry_by_content_attributes(self, content_uuid: str) -> Dict[str, Any]:
        """Find telemetry by looking at content attributes and matching against telemetry records.
        
        Args:
            content_uuid: UUID of the content in the graphiti database
            
        Returns:
            Dictionary with telemetry information or empty dict if not found
        """
        # Get content attributes
        content_query = f"""
        MATCH (c {{uuid: $content_uuid, group_id: '{self.CONTENT_GROUP_ID}'}})
        RETURN c.title as title, c.name as name, labels(c) as labels
        """
        params = {"content_uuid": content_uuid}
        
        content_result = await self.run_query(content_query, params)
        if not content_result or len(content_result) == 0:
            logger.warning(f"Content with UUID {content_uuid} not found")
            return {}
            
        # Extract attributes for matching
        title = content_result[0].get('title')
        name = content_result[0].get('name')
        
        # Try to find matching telemetry
        if title or name:
            search_term = title or name
            telemetry_query = f"""
            MATCH (l:EpisodeProcessingLog {{group_id: '{self.TELEMETRY_GROUP_ID}'}})
            WHERE l.original_name = $search_term OR l.episode_name = $search_term
               OR l.original_name CONTAINS $search_term OR l.episode_name CONTAINS $search_term
            RETURN l.episode_name as episode_name
            """
            
            telemetry_result = await self.run_query(telemetry_query, {"search_term": search_term})
            if telemetry_result and len(telemetry_result) > 0 and telemetry_result[0].get('episode_name'):
                logger.info(f"Found telemetry for content {content_uuid} by matching with {search_term}")
                return await self.get_episode_info(telemetry_result[0]['episode_name'])
        
        # No matching telemetry found
        logger.info(f"No telemetry found for content UUID {content_uuid}")
        return {}
