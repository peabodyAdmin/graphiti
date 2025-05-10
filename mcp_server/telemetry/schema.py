"""
Schema definitions for episode processing telemetry in Neo4j.
"""

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
