"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from neo4j import AsyncDriver

from graphiti_core.edges import GroupRegistryEdge
from graphiti_core.helpers import DEFAULT_DATABASE
from graphiti_core.nodes import EpisodicNode

logger = logging.getLogger(__name__)

async def create_group_registry_edges(driver: AsyncDriver) -> Dict[str, Any]:
    """
    Create BELONGS_TO edges from episodes to their group registry entries.
    
    This function finds all Episodic nodes and connects them to their corresponding
    GroupRegistry nodes based on the group_id property.
    
    Args:
        driver: Neo4j AsyncDriver instance
        
    Returns:
        Dictionary with statistics about the operation
    """
    # Find all episodes and their group_ids that don't already have a BELONGS_TO edge
    result = await driver.execute_query(
        """
        MATCH (e:Episodic)
        WHERE e.group_id IS NOT NULL
        AND NOT EXISTS {
            MATCH (e)-[:BELONGS_TO]->(:GroupRegistry)
        }
        RETURN e.uuid AS episode_uuid, e.group_id AS group_id
        """,
        database_=DEFAULT_DATABASE
    )
    
    # Statistics
    stats = {
        "total_episodes_processed": len(result[0]),
        "edges_created": 0,
        "errors": 0,
        "missing_group_registry": 0
    }
    
    # Process each episode
    for record in result[0]:
        episode_uuid = record["episode_uuid"]
        group_id = record["group_id"]
        
        # Check if the GroupRegistry node exists for this group_id
        registry_result = await driver.execute_query(
            """
            MATCH (g:GroupRegistry {group_id: $group_id})
            RETURN g.uuid AS registry_uuid
            """,
            group_id=group_id,
            database_=DEFAULT_DATABASE
        )
        
        # If the GroupRegistry node doesn't exist, create it
        if not registry_result[0]:
            logger.info(f"Creating GroupRegistry for group_id: {group_id}")
            
            # First, ensure the GroupRegistryRoot exists
            await driver.execute_query(
                """
                MERGE (root:GroupRegistryRoot {name: 'Group Registry'})
                """,
                database_=DEFAULT_DATABASE
            )
            
            # Create the GroupRegistry node and connect it to the root
            await driver.execute_query(
                """
                MATCH (root:GroupRegistryRoot {name: 'Group Registry'})
                MERGE (g:GroupRegistry {group_id: $group_id})
                ON CREATE SET 
                    g.created_at = datetime(),
                    g.creator = 'system',
                    g.description = $description,
                    g.name = $group_id
                MERGE (root)-[:CONTAINS]->(g)
                """,
                group_id=group_id,
                description=f"Auto-created group for {group_id}",
                database_=DEFAULT_DATABASE
            )
            
            stats["missing_group_registry"] += 1
        
        try:
            # Create the edge
            edge = GroupRegistryEdge(
                uuid=str(uuid4()),
                source_node_uuid=episode_uuid,
                target_node_uuid=None,  # Will be set by the query
                group_id=group_id,
                created_at=datetime.now(timezone.utc)
            )
            
            await edge.save(driver)
            stats["edges_created"] += 1
            
        except Exception as e:
            logger.error(f"Error creating edge for episode {episode_uuid}: {str(e)}")
            stats["errors"] += 1
    
    logger.info(f"Group registry edge creation complete: {stats}")
    return stats

async def create_group_registry_edge_for_episode(
    driver: AsyncDriver,
    episode: EpisodicNode
) -> Optional[GroupRegistryEdge]:
    """
    Create a BELONGS_TO edge from a specific episode to its group registry entry.
    
    If the GroupRegistry node doesn't exist for the episode's group_id, it will be created.
    
    Args:
        driver: Neo4j AsyncDriver instance
        episode: The EpisodicNode to connect to its group registry
        
    Returns:
        The created GroupRegistryEdge or None if the episode has no group_id
    """
    if not episode.group_id:
        logger.debug(f"Episode {episode.uuid} has no group_id, skipping group registry edge creation")
        return None
    
    # Check if the GroupRegistry node exists for this group_id
    registry_result = await driver.execute_query(
        """
        MATCH (g:GroupRegistry {group_id: $group_id})
        RETURN g.uuid AS registry_uuid
        """,
        group_id=episode.group_id,
        database_=DEFAULT_DATABASE
    )
    
    # If the GroupRegistry node doesn't exist, create it
    if not registry_result[0]:
        logger.info(f"Creating GroupRegistry for group_id: {episode.group_id}")
        
        # First, ensure the GroupRegistryRoot exists
        await driver.execute_query(
            """
            MERGE (root:GroupRegistryRoot {name: 'Group Registry'})
            """,
            database_=DEFAULT_DATABASE
        )
        
        # Create the GroupRegistry node and connect it to the root
        await driver.execute_query(
            """
            MATCH (root:GroupRegistryRoot {name: 'Group Registry'})
            MERGE (g:GroupRegistry {group_id: $group_id})
            ON CREATE SET 
                g.created_at = datetime(),
                g.creator = 'system',
                g.description = $description,
                g.name = $group_id
            MERGE (root)-[:CONTAINS]->(g)
            """,
            group_id=episode.group_id,
            description=f"Auto-created group for {episode.group_id}",
            database_=DEFAULT_DATABASE
        )
    
    # Check if the edge already exists
    edge_exists_result = await driver.execute_query(
        """
        MATCH (e:Episodic {uuid: $episode_uuid})-[:BELONGS_TO]->(:GroupRegistry {group_id: $group_id})
        RETURN count(*) AS edge_count
        """,
        episode_uuid=episode.uuid,
        group_id=episode.group_id,
        database_=DEFAULT_DATABASE
    )
    
    if edge_exists_result[0][0]["edge_count"] > 0:
        logger.debug(f"Edge already exists for episode {episode.uuid} to group registry {episode.group_id}")
        return None
    
    try:
        # Create the edge
        edge = GroupRegistryEdge(
            uuid=str(uuid4()),
            source_node_uuid=episode.uuid,
            target_node_uuid=None,  # Will be set by the query
            group_id=episode.group_id,
            created_at=datetime.now(timezone.utc)
        )
        
        await edge.save(driver)
        logger.debug(f"Created group registry edge for episode {episode.uuid} to group {episode.group_id}")
        return edge
        
    except Exception as e:
        logger.error(f"Error creating edge for episode {episode.uuid}: {str(e)}")
        return None

async def get_episodes_by_group_registry(
    driver: AsyncDriver, 
    group_id: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get episodes that belong to a specific group registry.
    
    Args:
        driver: Neo4j AsyncDriver instance
        group_id: The group_id to find episodes for
        limit: Optional limit on the number of episodes to return
        
    Returns:
        List of episode data dictionaries
    """
    limit_clause = f"LIMIT {limit}" if limit is not None else ""
    
    result = await driver.execute_query(
        f"""
        MATCH (e:Episodic)-[:BELONGS_TO]->(g:GroupRegistry {{group_id: $group_id}})
        RETURN e
        ORDER BY e.created_at DESC
        {limit_clause}
        """,
        group_id=group_id,
        database_=DEFAULT_DATABASE
    )
    
    episodes = []
    for record in result[0]:
        node = record["e"]
        episode_data = dict(node.items())
        episodes.append(episode_data)
    
    return episodes
