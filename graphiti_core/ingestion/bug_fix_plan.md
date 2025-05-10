# Graphiti Episode Ingestion Bug Fix Implementation Plan

This document outlines the step-by-step implementation plan for addressing the episode ingestion pipeline failures documented in the bug report. Each task has a checkbox that can be marked when completed.

## Phase 1: MCP Server Telemetry & Diagnostic System

### Neo4j Telemetry Schema
- [ ] Define telemetry graph schema in `/mcp_server/telemetry/schema.py`
  ```python
  # Schema for episode processing telemetry
  # All telemetry nodes and relationships will use group_id "graphiti_logs"
  
  # Episode Processing Log Node
  EPISODE_LOG_SCHEMA = {
      "labels": ["EpisodeProcessingLog"],
      "properties": {
          "episode_id": "string",     # The unique episode ID (EP1234:title format)
          "original_name": "string",  # Original name before unique naming
          "group_id": "string",       # Source group_id of the episode
          "status": "string",         # 'started', 'completed', 'failed'
          "start_time": "datetime",
          "end_time": "datetime",
          "processing_time_ms": "int"
      }
  }
  
  # Processing Step Node
  PROCESSING_STEP_SCHEMA = {
      "labels": ["ProcessingStep"],
      "properties": {
          "step_name": "string",     # e.g., 'extraction', 'node_resolution', etc.
          "start_time": "datetime",
          "end_time": "datetime",
          "status": "string",        # 'success', 'warning', 'error'
          "data": "json"            # Step-specific data (node counts, etc.)
      }
  }
  
  # Error Log Node
  ERROR_LOG_SCHEMA = {
      "labels": ["ProcessingError"],
      "properties": {
          "error_type": "string",    # Exception class name
          "error_message": "string",
          "stack_trace": "string",
          "context": "json",         # Additional context-specific data
          "resolution_status": "string", # 'unresolved', 'retry', 'resolved'
          "resolution_details": "string"
      }
  }
  
  # Relationship Types
  RELATIONSHIP_TYPES = {
      "PROCESSED": {                 # Episode -> ProcessingStep
          "properties": {}
      },
      "GENERATED_ERROR": {           # ProcessingStep -> Error
          "properties": {
              "affected_entity": "string",  # Optional: ID of entity involved
              "error_context": "json"       # Additional error context
          }
      },
      "RESOLVED_BY_RETRY": {         # Error -> ProcessingStep (retry attempt)
          "properties": {
              "retry_attempt": "int",
              "retry_strategy": "string"   # What strategy was used to resolve
          }
      }
  }
  ```

### Direct Neo4j Connection for Telemetry
- [ ] Create Neo4j telemetry client in `/mcp_server/telemetry/neo4j_client.py`
  ```python
  class TelemetryNeo4jClient:
      """Direct Neo4j client for telemetry, bypassing Graphiti but using same connection details."""
      
      def __init__(self, uri, user, password, database="neo4j"):
          self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
          self.database = database
      
      async def record_episode_start(self, episode_id, original_name, group_id):
          """Record the start of episode processing"""
          query = """
          CREATE (l:EpisodeProcessingLog {episode_id: $episode_id, original_name: $original_name, 
                                       group_id: $group_id, status: 'started', 
                                       start_time: datetime(), group_id: 'graphiti_logs'})
          RETURN l
          """
          params = {"episode_id": episode_id, "original_name": original_name, "group_id": group_id}
          return await self.run_query(query, params)
      
      async def record_processing_step(self, episode_id, step_name, status, data=None):
          """Record a processing step for an episode"""
          # Similar implementation with appropriate query
          pass
      
      async def record_error(self, episode_id, step_name, error_type, error_message, 
                           stack_trace, context=None):
          """Record an error that occurred during processing"""
          # Create error node and GENERATED_ERROR relationship
          pass
      
      async def run_query(self, query, params=None):
          """Run a Cypher query against Neo4j"""
          async with self.driver.session(database=self.database) as session:
              result = await session.run(query, params or {})
              return await result.data()
  ```

### Instrumentation Hook Points
- [ ] Add telemetry hooks in `/mcp_server/services/episode_processor.py`
  ```python
  async def process_episode_queue(clients, telemetry_client, group_id, episode_data):
      # Record start of processing
      await telemetry_client.record_episode_start(
          episode_id=episode_data.name,
          original_name=episode_data.original_name,
          group_id=group_id
      )
      
      max_retries = 5
      retry_count = 0
      
      while retry_count < max_retries:
          try:
              # Record processing step start
              await telemetry_client.record_processing_step(
                  episode_id=episode_data.name,
                  step_name="ingestion", 
                  status="started"
              )
              
              # Actual processing
              await process_func()
              
              # Record success
              await telemetry_client.record_processing_step(
                  episode_id=episode_data.name,
                  step_name="ingestion", 
                  status="success"
              )
              await telemetry_client.record_episode_completion(
                  episode_id=episode_data.name,
                  status="completed"
              )
              break
          except (DatabaseConnectionError, TimeoutError) as e:
              # Record transient error
              await telemetry_client.record_error(
                  episode_id=episode_data.name,
                  step_name="ingestion",
                  error_type=type(e).__name__,
                  error_message=str(e),
                  stack_trace=traceback.format_exc(),
                  context={"retry_count": retry_count}
              )
              retry_count += 1
              await asyncio.sleep(3 ** retry_count)
              logger.warning(f"Retrying episode processing (attempt {retry_count}/{max_retries})")
          except EntityNameConflictError as e:
              # Record conflict error with specific entity details
              await telemetry_client.record_error(
                  episode_id=episode_data.name,
                  step_name="ingestion",
                  error_type="EntityNameConflictError",
                  error_message=str(e),
                  stack_trace=traceback.format_exc(),
                  context={
                      "conflicting_entity": e.entity_id,
                      "conflict_type": "name_collision"
                  }
              )
              logger.warning(f"Entity name conflict detected: {str(e)}")
              await resolve_name_conflict(episode_data)
              retry_count += 1
          except Exception as e:
              # Record unrecoverable error
              await telemetry_client.record_error(
                  episode_id=episode_data.name,
                  step_name="ingestion",
                  error_type=type(e).__name__,
                  error_message=str(e),
                  stack_trace=traceback.format_exc(),
                  context={"unrecoverable": True}
              )
              logger.error(f"Unrecoverable error: {str(e)}")
              logger.error(traceback.format_exc())
              await store_failed_episode(episode_data)
              
              # Mark episode as failed
              await telemetry_client.record_episode_completion(
                  episode_id=episode_data.name,
                  status="failed"
              )
              break
  ```

- [ ] Add telemetry hooks in `/graphiti_core/graphiti.py`
  ```python
  # Add in both add_episode and add_episode_bulk methods:
  
  # At start of processing
  if telemetry_client:
      await telemetry_client.record_processing_step(
          episode_id=episode.name,
          step_name="node_extraction", 
          status="started"
      )
  
  # After successful extraction
  if telemetry_client:
      await telemetry_client.record_processing_step(
          episode_id=episode.name,
          step_name="node_extraction", 
          status="success",
          data={"node_count": len(nodes), "edge_count": len(edges)}
      )
  
  # In exception handlers
  except Exception as e:
      if telemetry_client:
          await telemetry_client.record_error(
              episode_id=episode.name,
              step_name="current_step_name",
              error_type=type(e).__name__,
              error_message=str(e),
              stack_trace=traceback.format_exc()
          )
      raise e
  ```

### Telemetry Dashboard and Analysis
- [ ] Create diagnostic queries in `/mcp_server/telemetry/diagnostic_queries.py`
  ```python
  # Queries to analyze telemetry data
  
  # Get processing history for a specific episode
  EPISODE_HISTORY_QUERY = """
  MATCH (log:EpisodeProcessingLog {episode_id: $episode_id, group_id: 'graphiti_logs'})
  OPTIONAL MATCH (log)-[:PROCESSED]->(step:ProcessingStep)
  OPTIONAL MATCH (step)-[:GENERATED_ERROR]->(error:ProcessingError)
  RETURN log, step, error
  ORDER BY step.start_time
  """
  
  # Find common error patterns across episodes
  ERROR_PATTERNS_QUERY = """
  MATCH (error:ProcessingError)<-[:GENERATED_ERROR]-(step:ProcessingStep)<-[:PROCESSED]-(log:EpisodeProcessingLog)
  WHERE log.group_id = 'graphiti_logs'
  RETURN error.error_type, count(distinct log) as affected_episodes,
         collect(distinct log.episode_id)[..10] as sample_episodes
  ORDER BY affected_episodes DESC
  """
  
  # Get episodes with specific error types
  EPISODES_WITH_ERROR_TYPE_QUERY = """
  MATCH (log:EpisodeProcessingLog {group_id: 'graphiti_logs'})-[:PROCESSED]->(:ProcessingStep)-[:GENERATED_ERROR]->
        (error:ProcessingError {error_type: $error_type})
  RETURN log.episode_id, log.original_name, error.error_message, error.context
  """
  ```

- [ ] Create MCP diagnostic tools in `/mcp_server/api/diagnostics.py`
  ```python
  @router.get("/api/diagnostics/episodes/{episode_id}/trace")
  async def get_episode_trace(episode_id: str, telemetry_client: TelemetryNeo4jClient = Depends(get_telemetry_client)):
      """Get the full processing trace for an episode"""
      result = await telemetry_client.run_query(EPISODE_HISTORY_QUERY, {"episode_id": episode_id})
      return format_episode_trace(result)
  
  @router.get("/api/diagnostics/errors/patterns")
  async def get_error_patterns(telemetry_client: TelemetryNeo4jClient = Depends(get_telemetry_client)):
      """Get patterns of errors across episodes"""
      result = await telemetry_client.run_query(ERROR_PATTERNS_QUERY)
      return result
  
  @router.get("/api/diagnostics/errors/{error_type}/episodes")
  async def get_episodes_with_error(error_type: str, telemetry_client: TelemetryNeo4jClient = Depends(get_telemetry_client)):
      """Get all episodes affected by a specific error type"""
      result = await telemetry_client.run_query(EPISODES_WITH_ERROR_TYPE_QUERY, {"error_type": error_type})
      return result
  ```

### Telemetry Infrastructure Setup
- [ ] Create database indices for telemetry data in `/mcp_server/telemetry/schema_setup.py`
  ```python
  # Cypher queries to set up telemetry schema
  
  CREATE_INDICES = [
      "CREATE INDEX episode_log_id_idx IF NOT EXISTS FOR (l:EpisodeProcessingLog) ON (l.episode_id)",
      "CREATE INDEX error_type_idx IF NOT EXISTS FOR (e:ProcessingError) ON (e.error_type)"
  ]
  
  async def setup_telemetry_schema(driver):
      """Set up the Neo4j schema for telemetry data"""
      async with driver.session() as session:
          for index_query in CREATE_INDICES:
              await session.run(index_query)
  ```

- [ ] Initialize telemetry in MCP server startup in `/mcp_server/main.py`
  ```python
  # Initialize telemetry client
  telemetry_client = TelemetryNeo4jClient(
      uri=settings.neo4j_uri,
      user=settings.neo4j_user,
      password=settings.neo4j_password,
      database=settings.neo4j_database
  )
  
  # Set up telemetry schema
  await setup_telemetry_schema(telemetry_client.driver)
  
  # Make telemetry client available to dependency injection
  app.dependency_overrides[get_telemetry_client] = lambda: telemetry_client
  ```


## Phase 2: Unique Episode Naming System

### Neo4j Counter Setup
- [ ] Create Neo4j Cypher queries for counter operations in `/graphiti_core/utils/graph_data_operations.py`
- [ ] Add indices for counter node lookups in `/graphiti_core/utils/maintenance/graph_data_operations.py`
- [ ] Ensure proper transaction handling for counter operations in `/graphiti_core/graphiti.py`

### Episode Naming Implementation
- [ ] Create `assign_unique_episode_name` function in `/graphiti_core/nodes.py`
  ```python
  async def assign_unique_episode_name(clients, original_name):
      # Get the next global episode counter using Neo4j under graphiti_internal group
      query = """
      MERGE (c:Counter {name: 'episode_counter', group_id: 'graphiti_internal'})
      ON CREATE SET c.value = 1
      ON MATCH SET c.value = c.value + 1
      RETURN c.value as new_counter
      """
      
      result = await clients.neo4j.run_query(query)
      counter = result[0]['new_counter']
      unique_name = f"EP{counter}:{original_name}"
      return unique_name
  ```
- [ ] Modify `add_episode` method in `/graphiti_core/graphiti.py` to use unique naming
  ```python
  if not episode_data.name.startswith("EP"):
      episode_data.name = await assign_unique_episode_name(clients, episode_data.name)
  ```
- [ ] Modify `add_episode_bulk` in `/graphiti_core/graphiti.py` to apply the same naming pattern
- [ ] Create validation function in `/graphiti_core/nodes.py` to prevent clients from using reserved prefix
  ```python
  def validate_client_episode_name(name):
      if re.match(r'^EP\d+:', name):
          raise InvalidEpisodeNameError("Episode names cannot use the reserved 'EP#:' prefix format")
  ```
- [ ] Implement validation in API endpoints in `/mcp_server/api/episodes.py`

## Phase 3: MCP Server Error Handling

### Error Classification System
- [ ] Define custom exception types for common failures in `/graphiti_core/errors.py`
  - [ ] `EntityNameConflictError`
  - [ ] `DatabaseConnectionError`
  - [ ] Other specific error types needed
- [ ] Create error classifier in `/mcp_server/utils/error_handling.py` to categorize generic exceptions
  ```python
  def classify_error(exception):
      # Logic to classify generic exceptions into specific types
      pass
  ```

### Enhanced Retry Mechanism
- [ ] Modify `process_episode_queue` in `/mcp_server/services/episode_processor.py` to implement the new retry logic
  ```python
  async def process_episode_queue(clients, group_id, episode_data):
      max_retries = 5
      retry_count = 0
      
      while retry_count < max_retries:
          try:
              await process_func()
              break
          except (DatabaseConnectionError, TimeoutError) as e:
              retry_count += 1
              await asyncio.sleep(3 ** retry_count)
              logger.warning(f"Retrying episode processing (attempt {retry_count}/{max_retries})")
          except EntityNameConflictError as e:
              logger.warning(f"Entity name conflict detected: {str(e)}")
              await resolve_name_conflict(episode_data)
              retry_count += 1
          except Exception as e:
              logger.error(f"Unrecoverable error: {str(e)}")
              logger.error(traceback.format_exc())
              await store_failed_episode(episode_data)
              break
  ```
- [ ] Implement `resolve_name_conflict` function in `/mcp_server/services/conflict_resolver.py` for handling specific conflict cases
- [ ] Create `store_failed_episode` function in `/mcp_server/services/failure_storage.py` for persisting failed episodes

### Logging Enhancements
- [ ] Update logger configuration in `/mcp_server/config/logging.py` to include stack traces
- [ ] Add more context to log messages in both `/graphiti_core/graphiti.py` and `/mcp_server/services/episode_processor.py`
- [ ] Implement more granular logging levels in `/mcp_server/config/logging.py` for different error severities

## Phase 4: Node Resolution Improvements

### Entity-Episode Distinction
- [ ] Modify episode model in `/graphiti_core/models/episodic_node.py` to always include 'Episode' label
  ```python
  episode.labels = ['Episode'] + episode.labels
  ```
- [ ] Update Neo4j queries in `/graphiti_core/utils/query_operations.py` to filter by label where appropriate
- [ ] Modify node resolution logic in `/graphiti_core/nodes.py` to respect labels during deduplication

### UUID Remapping Safety
- [ ] Add validation checks in the UUID remapping process in `/graphiti_core/utils/node_operations.py`
  ```python
  # Before remapping
  if extracted_node.labels and 'Episode' in extracted_node.labels:
      # Skip remapping or handle specially
  ```
- [ ] Implement consistency checks after remapping in `/graphiti_core/utils/node_operations.py` to verify integrity

### Database Constraints
- [ ] Add uniqueness constraints in Neo4j for episode identifiers in `/graphiti_core/utils/maintenance/graph_data_operations.py`
  ```cypher
  CREATE CONSTRAINT unique_episode_id IF NOT EXISTS 
  ON (e:Episode) ASSERT e.id IS UNIQUE
  ```
- [ ] Add safeguards in application code in `/graphiti_core/graphiti.py` to respect constraints

## Phase 5: Testing & Validation

### Unit Tests
- [ ] Create tests for unique episode name generation in `/tests/graphiti_core/test_naming.py`
- [ ] Test error handling and retry mechanisms in `/tests/mcp_server/test_error_handling.py`
- [ ] Validate UUID remapping with conflict scenarios in `/tests/graphiti_core/test_node_resolution.py`

### Integration Tests
- [ ] Test full episode ingestion pipeline with simulated errors in `/tests/integration/test_ingestion_pipeline.py`
- [ ] Verify episode retention with various error conditions in `/tests/integration/test_error_scenarios.py`
- [ ] Ensure conflicts between episode names and entities are handled correctly in `/tests/integration/test_name_conflicts.py`

### Performance Testing
- [ ] Measure impact of naming system on ingestion throughput in `/tests/performance/test_naming_system.py`
- [ ] Test retry behavior under load in `/tests/performance/test_retry_mechanism.py`
- [ ] Verify database performance with new constraints in `/tests/performance/test_db_constraints.py`

## Phase 6: Deployment & Monitoring

### Deployment
- [ ] Prepare database migration scripts for new constraints in `/deployment/migrations/add_episode_constraints.cypher`
- [ ] Create deployment plan with rollback procedures in `/deployment/plans/episode_bugfix_deploy.md`
- [ ] Document changes for operations team in `/docs/operations/episode_bugfix.md`

### Monitoring Enhancements
- [ ] Add metrics for tracking failed episodes in `/mcp_server/monitoring/episode_metrics.py`
- [ ] Create alerts for retry exhaustion in `/monitoring/alerting/episode_failure_alerts.py`
- [ ] Track episode counter usage and conflicts in `/monitoring/dashboards/episode_counter_dashboard.json`

### Documentation
- [ ] Update API documentation with new naming requirements in `/docs/api/episodes.md`
- [ ] Document error handling expectations for clients in `/docs/client/error_handling.md`
- [ ] Create troubleshooting guide for operations in `/docs/operations/troubleshooting.md`

## Phase 7: Follow-up

### Technical Debt
- [ ] Refactor other exception handling patterns in `/graphiti_core/graphiti.py` and `/mcp_server/services/`
- [ ] Review and improve other error recovery mechanisms in `/mcp_server/services/`
- [ ] Standardize logging formats across services in `/mcp_server/config/logging.py` and `/graphiti_core/utils/logging.py`

### Backfill Strategy
- [ ] Develop plan for renaming existing episodes if needed in `/scripts/migration/rename_episodes.py`
- [ ] Create scripts to verify and repair any damaged references in `/scripts/migration/repair_references.py`
- [ ] Test backfill procedure in staging environment using `/scripts/migration/test_backfill.py`
