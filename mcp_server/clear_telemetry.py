#!/usr/bin/env python3
"""
Quick script to clear telemetry data and restart with clean state
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telemetry.neo4j_client import TelemetryNeo4jClient

async def clear_telemetry():
    # Load environment variables
    project_root = Path(__file__).parent.parent.absolute()
    load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
    
    # Initialize the telemetry client
    client = TelemetryNeo4jClient(
        os.getenv('NEO4J_URI'),
        os.getenv('NEO4J_USER'),
        os.getenv('NEO4J_PASSWORD')
    )
    
    try:
        print("Clearing all telemetry data...")
        result = await client.clear_telemetry_data()
        print("Telemetry data cleared successfully.")
        
        # Display the current state
        stats = await client.get_telemetry_stats()
        print("\nCurrent telemetry stats:")
        print(stats or "No data available")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(clear_telemetry())
