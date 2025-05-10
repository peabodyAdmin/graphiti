"""
Neo4j client for telemetry, bypassing Graphiti but using same connection details.
"""

import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase
from neo4j.graph import Node, Relationship

class TelemetryNeo4jClient:
    """Direct Neo4j client for telemetry, bypassing Graphiti but using same connection details."""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """Initialize the telemetry client with Neo4j connection details."""
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.database = database
    
    async def record_episode_start(self, episode_id: str, original_name: str, group_id: str):
        """Record the start of episode processing."""
        query = """
        CREATE (l:EpisodeProcessingLog {
            episode_id: $episode_id, 
            original_name: $original_name, 
            group_id: $group_id, 
            status: 'started', 
            start_time: datetime(), 
            group_id: 'graphiti_logs'
        })
        RETURN l
        """
        params = {"episode_id": episode_id, "original_name": original_name, "group_id": group_id}
        return await self.run_query(query, params)
    
    async def record_episode_completion(self, episode_id: str, status: str):
        """Record the completion of episode processing."""
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        SET l.status = $status, 
            l.end_time = datetime(),
            l.processing_time_ms = duration.between(l.start_time, datetime()).milliseconds
        RETURN l
        """
        params = {"episode_id": episode_id, "status": status}
        return await self.run_query(query, params)
    
    async def record_processing_step(self, episode_id: str, step_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Record a processing step for an episode."""
        data_str = json.dumps(data) if data else "{}"
        
        # First create the processing step node
        create_step_query = """
        CREATE (s:ProcessingStep {
            step_name: $step_name,
            start_time: CASE WHEN $status = 'started' THEN datetime() ELSE null END,
            end_time: CASE WHEN $status != 'started' THEN datetime() ELSE null END,
            status: $status,
            data: $data
        })
        RETURN s
        """
        create_params = {"step_name": step_name, "status": status, "data": data_str}
        step_result = await self.run_query(create_step_query, create_params)
        
        if not step_result:
            return None
        
        # Then create relationship to the episode
        relate_query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        MATCH (s:ProcessingStep) WHERE id(s) = $step_id
        CREATE (l)-[r:PROCESSED]->(s)
        RETURN r
        """
        relate_params = {"episode_id": episode_id, "step_id": step_result[0]['s'].id}
        return await self.run_query(relate_query, relate_params)
    
    async def update_processing_step(self, episode_id: str, step_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Update an existing processing step with new status and data."""
        data_str = json.dumps(data) if data else None
        
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
        SET s.status = $status,
            s.end_time = CASE WHEN $status != 'started' THEN datetime() ELSE s.end_time END,
            s.data = CASE WHEN $data IS NOT NULL THEN $data ELSE s.data END
        RETURN s
        """
        params = {"episode_id": episode_id, "step_name": step_name, "status": status, "data": data_str}
        return await self.run_query(query, params)
    
    async def record_error(self, episode_id: str, step_name: str, error_type: str, error_message: str, 
                         stack_trace: str, context: Optional[Dict[str, Any]] = None):
        """Record an error that occurred during processing."""
        context_str = json.dumps(context) if context else "{}"
        
        # First create the error node
        create_error_query = """
        CREATE (e:ProcessingError {
            error_type: $error_type,
            error_message: $error_message,
            stack_trace: $stack_trace,
            context: $context,
            resolution_status: 'unresolved',
            resolution_details: ''
        })
        RETURN e
        """
        error_params = {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "context": context_str
        }
        error_result = await self.run_query(create_error_query, error_params)
        
        if not error_result:
            return None
        
        # Find the processing step and create relationship
        relate_query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})-[:PROCESSED]->(s:ProcessingStep {step_name: $step_name})
        MATCH (e:ProcessingError) WHERE id(e) = $error_id
        CREATE (s)-[r:GENERATED_ERROR {
            affected_entity: $affected_entity,
            error_context: $error_context
        }]->(e)
        RETURN r
        """
        relate_params = {
            "episode_id": episode_id,
            "step_name": step_name,
            "error_id": error_result[0]['e'].id,
            "affected_entity": context.get("affected_entity", "") if context else "",
            "error_context": context_str
        }
        return await self.run_query(relate_query, relate_params)
    
    async def record_retry(self, episode_id: str, error_id: int, retry_attempt: int, retry_strategy: str):
        """Record a retry attempt for an error."""
        query = """
        MATCH (l:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
        MATCH (e:ProcessingError) WHERE id(e) = $error_id
        CREATE (e)-[r:RESOLVED_BY_RETRY {
            retry_attempt: $retry_attempt,
            retry_strategy: $retry_strategy
        }]->(l)
        RETURN r
        """
        params = {
            "episode_id": episode_id,
            "error_id": error_id,
            "retry_attempt": retry_attempt,
            "retry_strategy": retry_strategy
        }
        return await self.run_query(query, params)
    
    async def run_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Run a Cypher query against Neo4j."""
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, params or {})
                return await result.data()
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            print(traceback.format_exc())
            return None
    
    async def close(self):
        """Close the Neo4j driver connection."""
        await self.driver.close()
