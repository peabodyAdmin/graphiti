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
        self.initialization_verified = False
        # Log connection details (without password)
        logger.info(f"Initialized Neo4j telemetry client: URI={uri}, Database={database}")
        

    
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
            
    async def record_episode_start(self, episode_id: str, original_name: str, group_id: str):
        """Record the start of episode processing.
        
        Args:
            episode_id: Unique identifier for the episode
            original_name: Original name of the episode
            group_id: The client's group_id (used as a reference for client_group_id)
        
        Note: All telemetry is stored under group_id='graphiti_logs' regardless of client group_id
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
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
        result = await self.run_query(query, params)
        
        # Create EpisodeTracking node for this processing attempt
        tracking_query = """
        CREATE (t:EpisodeTracking {
            episode_id: $episode_id,
            original_name: $original_name,
            client_group_id: $client_group_id,
            tracking_id: $tracking_id,
            attempt_number: $attempt_number,
            created_at: datetime(),
            status: 'in_progress',
            group_id: 'graphiti_logs'
        })
        WITH t
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        MERGE (l)-[r:TRACKED_BY]->(t)
        RETURN t
        """
        
        # Generate a unique tracking ID
        import uuid
        tracking_id = f"track_{uuid.uuid4().hex}"
        attempt_number = result[0]['l'].get('attempt_count') if result and len(result) > 0 and 'l' in result[0] else 1
        
        tracking_params = {
            "episode_id": episode_id,
            "original_name": original_name,
            "client_group_id": group_id,
            "tracking_id": tracking_id,
            "attempt_number": attempt_number
        }
        
        try:
            tracking_result = await self.run_query(tracking_query, tracking_params)
            logger.info(f"Created EpisodeTracking node {tracking_id} for episode {episode_id} (attempt {attempt_number})")
        except Exception as e:
            logger.error(f"Failed to create EpisodeTracking node for {episode_id}: {str(e)}")
        
        return result
    
    async def record_episode_completion(self, episode_id: str, status: str):
        """Record the completion of episode processing.
        
        Args:
            episode_id: Unique identifier for the episode
            status: Status to set ('completed' or 'failed')
        """
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        
        # 1. First update the episode log with completion status and calculate processing time
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        SET l.status = $status, 
            l.end_time = datetime(),
            l.processing_time_ms = duration.between(l.start_time, datetime()).milliseconds
        RETURN l, l.processing_time_ms as processing_time_ms
        """
        params = {"episode_id": episode_id, "status": status}
        result = await self.run_query(query, params)
        
        if not result:
            logger.warning(f"No episode found with id {episode_id} when trying to record completion")
            return None
            
        # 2. Create a separate EpisodeTiming node for better analytics
        try:
            processing_time_ms = result[0].get('processing_time_ms')
            timing_query = """
            CREATE (t:EpisodeTiming {
                episode_id: $episode_id,
                processing_time_ms: $processing_time_ms,
                status: $status,
                recorded_at: datetime(),
                group_id: 'graphiti_logs'
            })
            WITH t
            MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
            MERGE (l)-[r:HAS_TIMING]->(t)
            RETURN t
            """
            timing_params = {
                "episode_id": episode_id, 
                "processing_time_ms": processing_time_ms,
                "status": status
            }
            await self.run_query(timing_query, timing_params)
            logger.info(f"Created EpisodeTiming node for {episode_id} with processing time {processing_time_ms}ms")
            
            # 3. Create relationships between steps to show processing sequence
            steps_query = """
            MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(steps:ProcessingStep)
            WITH steps ORDER BY steps.start_time ASC
            WITH collect(steps) as ordered_steps
            UNWIND range(0, size(ordered_steps) - 2) as i
            WITH ordered_steps[i] as current, ordered_steps[i+1] as next
            MERGE (current)-[r:FOLLOWED_BY]->(next)
            RETURN count(r) as relationships_created
            """
            steps_result = await self.run_query(steps_query, {"episode_id": episode_id})
            if steps_result and len(steps_result) > 0 and 'relationships_created' in steps_result[0]:
                logger.info(f"Created {steps_result[0]['relationships_created']} step sequence relationships for {episode_id}")
            
            # 4. Update EpisodeTracking nodes for this episode
            tracking_update_query = """
            MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:TRACKED_BY]->(t:EpisodeTracking)
            WHERE t.status = 'in_progress'
            SET t.status = $status,
                t.completed_at = datetime(),
                t.processing_time_ms = $processing_time_ms
            RETURN t
            """
            tracking_params = {
                "episode_id": episode_id,
                "status": status,
                "processing_time_ms": processing_time_ms
            }
            tracking_update_result = await self.run_query(tracking_update_query, tracking_params)
            logger.info(f"Updated EpisodeTracking for {episode_id} with status {status} and processing time {processing_time_ms}ms")
            
        except Exception as e:
            logger.error(f"Error creating timing analytics for {episode_id}: {str(e)}")
            
        return result
    
    async def create_episode_log(self, episode_id: str, status: str = "in_progress"):
        """Create a new episode log node in the database.
        
        Args:
            episode_id: Unique identifier for the episode
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
                episode_id: $episode_id,
                group_id: 'graphiti_logs'
            })
            ON CREATE SET l.status = $status, 
                         l.created_at = datetime()
            RETURN l
            """
            params = {"episode_id": episode_id, "status": status}
            result = await self.run_query(query, params)
            return result
        except Exception as e:
            logger.error(f"Error creating episode log: {e}")
            return None
    
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
        # Ensure DB connectivity is verified
        await self.ensure_verified()
        logger.info(f"Recording processing step for episode {episode_id}: {step_name} - {status}")
        # Ensure the episode exists - create it if it doesn't
        check_episode_query = """
        MERGE (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        ON CREATE SET l.created_at = datetime(), l.status = 'in_progress'
        RETURN l
        """
        check_result = await self.run_query(check_episode_query, {"episode_id": episode_id})
        
        if not check_result:
            logger.error(f"Failed to ensure episode log exists for {episode_id}")
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
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        MATCH (s:ProcessingStep {step_id: $step_id})
        MERGE (l)-[r:PROCESSED]->(s)
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
            MATCH (e:ProcessingError {error_id: $error_id, group_id: 'graphiti_logs'})
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
        MATCH (l:EpisodeProcessingLog {client_group_id: $group_id, group_id: 'graphiti_logs'})
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
    
    async def get_episode_info(self, episode_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific episode.
        
        Args:
            episode_id: ID of the episode to retrieve
            
        Returns:
            Dictionary with episode information and processing steps
        """
        # Query for episode info
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        OPTIONAL MATCH (l)-[:PROCESSED]->(s:ProcessingStep)
        RETURN l, collect(s) as steps
        """
        params = {"episode_id": episode_id}
        
        result = await self.run_query(query, params)
        if not result or len(result) == 0:
            return {}
            
        episode_data = dict(result[0]['l'])
        steps_data = [dict(s) for s in result[0]['steps']]
        
        # Format datetime objects to strings
        for key in episode_data:
            if isinstance(episode_data[key], datetime):
                episode_data[key] = episode_data[key].isoformat()
                
        for step in steps_data:
            for key in step:
                if isinstance(step[key], datetime):
                    step[key] = step[key].isoformat()
        
        return {
            "info": episode_data,
            "steps": steps_data
        }
