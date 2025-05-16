#!/usr/bin/env python
"""
Utility script to create BELONGS_TO edges from episodes to their group registry entries.

This script connects all existing episodes to their corresponding group registry entries
by creating BELONGS_TO edges between them.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any

import dotenv
from neo4j import AsyncGraphDatabase

from graphiti_core.utils.maintenance.group_registry_operations import create_group_registry_edges

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

async def main() -> Dict[str, Any]:
    """
    Main function to create group registry edges for all episodes.
    
    Returns:
        Dictionary with statistics about the operation
    """
    # Load environment variables
    dotenv.load_dotenv()
    
    # Get Neo4j connection details from environment variables
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        neo4j_uri, auth=(neo4j_user, neo4j_password)
    )
    
    try:
        # Create the edges
        logger.info("Creating group registry edges for all episodes...")
        start_time = datetime.now(timezone.utc)
        
        stats = await create_group_registry_edges(driver)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Operation completed in {duration:.2f} seconds")
        logger.info(f"Total episodes processed: {stats['total_episodes_processed']}")
        logger.info(f"Edges created: {stats['edges_created']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Missing group registry entries: {stats['missing_group_registry']}")
        
        return stats
    finally:
        # Close the driver
        await driver.close()

if __name__ == "__main__":
    asyncio.run(main())
