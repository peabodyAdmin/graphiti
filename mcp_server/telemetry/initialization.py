"""
Telemetry initialization utilities.
"""

import logging
from mcp_server.telemetry.config import TelemetryConfig
from mcp_server.telemetry.neo4j_client import TelemetryNeo4jClient
from mcp_server.telemetry.schema_setup import setup_telemetry_schema

logger = logging.getLogger(__name__)

async def initialize_telemetry(config: TelemetryConfig, main_uri=None, main_user=None, main_password=None) -> TelemetryNeo4jClient:
    """
    Initialize the telemetry system based on configuration.
    
    Args:
        config: TelemetryConfig instance
        main_uri: Main application Neo4j URI (used if use_same_neo4j is True)
        main_user: Main application Neo4j username (used if use_same_neo4j is True)
        main_password: Main application Neo4j password (used if use_same_neo4j is True)
        
    Returns:
        Initialized TelemetryNeo4jClient instance or None if telemetry is disabled
    """
    if not config.enabled:
        logger.info("Telemetry is disabled")
        return None
    
    try:
        # Determine connection parameters
        if config.use_same_neo4j:
            if not main_uri or not main_user or not main_password:
                logger.warning("Cannot initialize telemetry: missing main Neo4j connection details")
                return None
                
            uri = main_uri
            user = main_user
            password = main_password
            database = config.neo4j_database
        else:
            if not config.neo4j_uri or not config.neo4j_user or not config.neo4j_password:
                logger.warning("Cannot initialize telemetry: missing telemetry Neo4j connection details")
                return None
                
            uri = config.neo4j_uri
            user = config.neo4j_user
            password = config.neo4j_password
            database = config.neo4j_database
        
        # Initialize telemetry client
        telemetry_client = TelemetryNeo4jClient(
            uri=uri,
            user=user,
            password=password,
            database=database
        )
        
        # Set up telemetry schema
        await setup_telemetry_schema(telemetry_client.driver)
        
        logger.info("Telemetry system initialized successfully")
        return telemetry_client
        
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {str(e)}")
        return None
