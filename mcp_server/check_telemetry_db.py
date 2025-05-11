#!/usr/bin/env python3
"""
Quick script to check telemetry database records
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telemetry.neo4j_client import TelemetryNeo4jClient

async def check_db():
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
        # Check telemetry episode logs
        result = await client.run_query('''
        MATCH (l:EpisodeProcessingLog) 
        RETURN l.episode_id, l.original_name, l.group_id, l.status, l.start_time
        ORDER BY l.start_time DESC
        ''')
        
        print('EpisodeProcessingLog records:')
        for r in result:
            print(r)
        
        print("\n-------------------------------\n")
        
        # Check processing steps
        steps_result = await client.run_query('''
        MATCH (s:ProcessingStep)
        RETURN s.step_name, s.status, s.start_time, s.end_time
        ''')
        
        print('ProcessingStep records:')
        for r in steps_result:
            print(r)
            
        print("\n-------------------------------\n")
        
        # Check error records
        error_result = await client.run_query('''
        MATCH (e:ProcessingError)
        RETURN e.error_type, e.error_message
        ''')
        
        print('ProcessingError records:')
        for r in error_result:
            print(r)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check_db())
