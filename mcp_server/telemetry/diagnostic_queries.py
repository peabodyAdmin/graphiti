"""
Queries to analyze telemetry data for diagnostic purposes.
"""

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

# Get episodes with specific error type
EPISODES_WITH_ERROR_TYPE_QUERY = """
MATCH (log:EpisodeProcessingLog {group_id: 'graphiti_logs'})-[:PROCESSED]->(:ProcessingStep)-[:GENERATED_ERROR]->
      (error:ProcessingError {error_type: $error_type})
RETURN log.episode_id, log.original_name, error.error_message, error.context
"""

# Find all episodes that failed in a specific processing step
STEP_FAILURES_QUERY = """
MATCH (log:EpisodeProcessingLog {group_id: 'graphiti_logs'})-[:PROCESSED]->(step:ProcessingStep {step_name: $step_name})
WHERE step.status = 'error'
RETURN log.episode_id, log.original_name, step.data, step.start_time, step.end_time
ORDER BY step.start_time DESC
"""

# Get overall processing statistics
PROCESSING_STATS_QUERY = """
MATCH (log:EpisodeProcessingLog {group_id: 'graphiti_logs'})
RETURN 
    count(log) as total_episodes,
    sum(CASE WHEN log.status = 'completed' THEN 1 ELSE 0 END) as completed,
    sum(CASE WHEN log.status = 'failed' THEN 1 ELSE 0 END) as failed,
    sum(CASE WHEN log.status = 'started' THEN 1 ELSE 0 END) as in_progress,
    avg(log.processing_time_ms) as avg_processing_time_ms
"""

# Get processing time distribution by step
STEP_TIMING_QUERY = """
MATCH (log:EpisodeProcessingLog {group_id: 'graphiti_logs'})-[:PROCESSED]->(step:ProcessingStep)
WHERE step.status IN ['success', 'warning', 'error'] AND step.end_time IS NOT NULL
WITH step.step_name as step_name, duration.between(step.start_time, step.end_time).milliseconds as duration_ms
RETURN 
    step_name,
    count(*) as count,
    avg(duration_ms) as avg_ms,
    min(duration_ms) as min_ms,
    max(duration_ms) as max_ms,
    percentileCont(duration_ms, 0.5) as median_ms,
    percentileCont(duration_ms, 0.95) as p95_ms
ORDER BY avg_ms DESC
"""

# Get recent errors
RECENT_ERRORS_QUERY = """
MATCH (error:ProcessingError)<-[:GENERATED_ERROR]-(step:ProcessingStep)<-[:PROCESSED]-(log:EpisodeProcessingLog)
WHERE log.group_id = 'graphiti_logs'
RETURN 
    log.episode_id, 
    step.step_name, 
    error.error_type, 
    error.error_message,
    step.end_time as error_time
ORDER BY error_time DESC
LIMIT 20
"""
