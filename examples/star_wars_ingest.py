"""
Script to ingest a Star Wars film description into Graphiti.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Neo4j connection parameters
neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')

if not neo4j_uri or not neo4j_user or not neo4j_password:
    raise ValueError('NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set')

# Star Wars film description
star_wars_description = """
In "Star Wars: The Empire Strikes Back," the Rebel Alliance faces devastating setbacks as the Galactic Empire, led by the menacing Darth Vader, launches an all-out assault on their hidden base on the ice planet Hoth, forcing a desperate evacuation; meanwhile, Luke Skywalker journeys to the remote swamp world of Dagobah to train with the enigmatic Jedi Master Yoda, while Han Solo, Princess Leia, and Chewbacca flee to Cloud City seeking refuge with Han's old friend Lando Calrissian, unaware that Vader has laid a trap that culminates in Han's capture, Luke's traumatic revelation about his parentage, and a climactic lightsaber duel that leaves the heroes' fate hanging in the balance.
"""

async def main():
    # Initialize Graphiti with Neo4j connection
    graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)

    try:
        # Initialize the graph database with indices (only needed once)
        await graphiti.build_indices_and_constraints()

        # Add Star Wars episode to the graph
        await graphiti.add_episode(
            name='Star Wars: The Empire Strikes Back',
            episode_body=star_wars_description,
            source=EpisodeType.text,
            source_description='Star Wars film description',
            reference_time=datetime.now(timezone.utc),
        )
        
        logger.info('Successfully added Star Wars film description to Graphiti')
        
        # Optional: Perform a search to verify the content was added
        print("\nSearching for: 'Who is Darth Vader?'")
        results = await graphiti.search('Who is Darth Vader?')
        
        # Print search results
        print('\nSearch Results:')
        for result in results:
            print(f'UUID: {result.uuid}')
            print(f'Fact: {result.fact}')
            if hasattr(result, 'valid_at') and result.valid_at:
                print(f'Valid from: {result.valid_at}')
            if hasattr(result, 'invalid_at') and result.invalid_at:
                print(f'Valid until: {result.invalid_at}')
            print('---')
            
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())
