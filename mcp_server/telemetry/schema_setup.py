"""
Schema setup utilities for telemetry data in Neo4j.
"""

from neo4j import AsyncDriver, AsyncGraphDatabase

# Cypher queries to set up telemetry schema
CREATE_INDICES = [
    "CREATE INDEX episode_log_id_idx IF NOT EXISTS FOR (l:EpisodeProcessingLog) ON (l.episode_id)",
    "CREATE INDEX error_type_idx IF NOT EXISTS FOR (e:ProcessingError) ON (e.error_type)",
    "CREATE INDEX step_name_idx IF NOT EXISTS FOR (s:ProcessingStep) ON (s.step_name)",
    "CREATE INDEX episode_log_status_idx IF NOT EXISTS FOR (l:EpisodeProcessingLog) ON (l.status)",
    "CREATE INDEX processing_logs_group_id_idx IF NOT EXISTS FOR (l:EpisodeProcessingLog) ON (l.group_id)"
]

async def setup_telemetry_schema(driver: AsyncDriver):
    """Set up the Neo4j schema for telemetry data."""
    async with driver.session() as session:
        for index_query in CREATE_INDICES:
            await session.run(index_query)
