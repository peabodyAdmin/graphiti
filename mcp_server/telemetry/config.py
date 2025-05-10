"""
Configuration for the telemetry system.
"""

import os
from pydantic import BaseModel, Field

class TelemetryConfig(BaseModel):
    """Configuration for the telemetry system.
    
    Controls whether telemetry is enabled and which features are active.
    """
    
    enabled: bool = Field(
        default=True,
        description="Whether telemetry is enabled."
    )
    use_same_neo4j: bool = Field(
        default=True,
        description="Whether to use the same Neo4j connection as the main application."
    )
    neo4j_uri: str = Field(
        default="",
        description="URI for Neo4j database specifically for telemetry (if different from main app)."
    )
    neo4j_user: str = Field(
        default="",
        description="Username for Neo4j specifically for telemetry (if different from main app)."
    )
    neo4j_password: str = Field(
        default="",
        description="Password for Neo4j specifically for telemetry (if different from main app)."
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Database name for Neo4j specifically for telemetry."
    )
    
    @classmethod
    def from_env(cls) -> 'TelemetryConfig':
        """Create telemetry configuration from environment variables."""
        return cls(
            enabled=os.environ.get("TELEMETRY_ENABLED", "true").lower() in ("true", "1", "yes"),
            use_same_neo4j=os.environ.get("TELEMETRY_USE_SAME_NEO4J", "true").lower() in ("true", "1", "yes"),
            neo4j_uri=os.environ.get("TELEMETRY_NEO4J_URI", ""),
            neo4j_user=os.environ.get("TELEMETRY_NEO4J_USER", ""),
            neo4j_password=os.environ.get("TELEMETRY_NEO4J_PASSWORD", ""),
            neo4j_database=os.environ.get("TELEMETRY_NEO4J_DATABASE", "neo4j"),
        )
