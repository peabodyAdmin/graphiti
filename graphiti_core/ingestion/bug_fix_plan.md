# Graphiti Episode Ingestion Bug Fix Implementation Plan

This document outlines the step-by-step implementation plan for addressing the episode ingestion pipeline failures documented in the bug report. Each task has a checkbox that can be marked when completed.

## Phase 1: Unique Episode Naming System

### Neo4j Counter Setup
- [ ] Create Neo4j Cypher queries for counter operations
- [ ] Add indices for counter node lookups
- [ ] Ensure proper transaction handling for counter operations

### Episode Naming Implementation
- [ ] Create `assign_unique_episode_name` function in appropriate module
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
- [ ] Modify `add_episode` method to use unique naming
  ```python
  if not episode_data.name.startswith("EP"):
      episode_data.name = await assign_unique_episode_name(clients, episode_data.name)
  ```
- [ ] Modify `add_episode_bulk` to apply the same naming pattern
- [ ] Create validation function to prevent clients from using reserved prefix
  ```python
  def validate_client_episode_name(name):
      if re.match(r'^EP\d+:', name):
          raise InvalidEpisodeNameError("Episode names cannot use the reserved 'EP#:' prefix format")
  ```
- [ ] Implement validation in API endpoints

## Phase 2: MCP Server Error Handling

### Error Classification System
- [ ] Define custom exception types for common failures
  - [ ] `EntityNameConflictError`
  - [ ] `DatabaseConnectionError`
  - [ ] Other specific error types needed
- [ ] Create error classifier to categorize generic exceptions
  ```python
  def classify_error(exception):
      # Logic to classify generic exceptions into specific types
      pass
  ```

### Enhanced Retry Mechanism
- [ ] Modify `process_episode_queue` to implement the new retry logic
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
- [ ] Implement `resolve_name_conflict` function for handling specific conflict cases
- [ ] Create `store_failed_episode` function for persisting failed episodes

### Logging Enhancements
- [ ] Update logger configuration to include stack traces
- [ ] Add more context to log messages (operation ID, timestamps, etc.)
- [ ] Implement more granular logging levels for different error severities

## Phase 3: Node Resolution Improvements

### Entity-Episode Distinction
- [ ] Modify episode model to always include 'Episode' label
  ```python
  episode.labels = ['Episode'] + episode.labels
  ```
- [ ] Update Neo4j queries to filter by label where appropriate
- [ ] Modify node resolution logic to respect labels during deduplication

### UUID Remapping Safety
- [ ] Add validation checks in the UUID remapping process
  ```python
  # Before remapping
  if extracted_node.labels and 'Episode' in extracted_node.labels:
      # Skip remapping or handle specially
  ```
- [ ] Implement consistency checks after remapping to verify integrity

### Database Constraints
- [ ] Add uniqueness constraints in Neo4j for episode identifiers
  ```cypher
  CREATE CONSTRAINT unique_episode_id IF NOT EXISTS 
  ON (e:Episode) ASSERT e.id IS UNIQUE
  ```
- [ ] Add safeguards in application code to respect constraints

## Phase 4: Testing & Validation

### Unit Tests
- [ ] Create tests for unique episode name generation
- [ ] Test error handling and retry mechanisms
- [ ] Validate UUID remapping with conflict scenarios

### Integration Tests
- [ ] Test full episode ingestion pipeline with simulated errors
- [ ] Verify episode retention with various error conditions
- [ ] Ensure conflicts between episode names and entities are handled correctly

### Performance Testing
- [ ] Measure impact of naming system on ingestion throughput
- [ ] Test retry behavior under load
- [ ] Verify database performance with new constraints

## Phase 5: Deployment & Monitoring

### Deployment
- [ ] Prepare database migration scripts for new constraints
- [ ] Create deployment plan with rollback procedures
- [ ] Document changes for operations team

### Monitoring Enhancements
- [ ] Add metrics for tracking failed episodes
- [ ] Create alerts for retry exhaustion
- [ ] Track episode counter usage and conflicts

### Documentation
- [ ] Update API documentation with new naming requirements
- [ ] Document error handling expectations for clients
- [ ] Create troubleshooting guide for operations

## Phase 6: Follow-up

### Technical Debt
- [ ] Refactor other exception handling patterns in the codebase
- [ ] Review and improve other error recovery mechanisms
- [ ] Standardize logging formats across services

### Backfill Strategy
- [ ] Develop plan for renaming existing episodes if needed
- [ ] Create scripts to verify and repair any damaged references
- [ ] Test backfill procedure in staging environment
