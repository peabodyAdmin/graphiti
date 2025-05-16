"""
Group registry system for managing Graphiti groups.

This module provides a formal registry to track metadata about each group in Neo4j,
including descriptions, creation timestamps, and usage statistics.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from neo4j import AsyncDriver

logger = logging.getLogger(__name__)

# Constants
PROTECTED_GROUPS = ['system', 'graphiti_logs', 'admin', 'graphiti_system']
GROUP_REGISTRY_LABEL = 'GroupRegistry'
GROUP_REGISTRY_ROOT_LABEL = 'GroupRegistryRoot'
GROUP_REGISTRY_ROOT_NAME = 'Group Registry'

class GroupRegistry:
    """Manage the group registry in Neo4j."""
    
    def __init__(self, driver: AsyncDriver):
        """Initialize with a Neo4j driver."""
        self.driver = driver
        
    async def initialize(self):
        """Ensure registry indices, constraints, and root node exist."""
        # Create constraints for uniqueness
        await self.driver.execute_query(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (g:{GROUP_REGISTRY_LABEL}) REQUIRE g.group_id IS UNIQUE"
        )
        
        # Create root node
        await self.driver.execute_query(
            f"MERGE (root:{GROUP_REGISTRY_ROOT_LABEL} {{name: $name}})",
            {"name": GROUP_REGISTRY_ROOT_NAME}
        )
        
        logger.info("Group registry initialized with root node")
        
    async def register_group(self, group_id: str, description: str, 
                             creator: str = "system", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Register a new group or update existing group information.
        
        Args:
            group_id: The unique group identifier
            description: Description of the group's purpose
            creator: Who created this group
            metadata: Additional metadata for the group
            
        Returns:
            Dictionary with group information
        """
        # Ensure registry is initialized
        await self.initialize()
        
        # Validate group_id
        if not self._is_valid_group_id(group_id):
            raise ValueError(f"Invalid group_id format: {group_id}")
            
        if self.is_protected_group(group_id):
            raise ValueError(f"Cannot modify protected group: {group_id}")
            
        # Create or update group in registry and connect to root
        query = f"""
        MATCH (root:{GROUP_REGISTRY_ROOT_LABEL} {{name: $root_name}})
        MERGE (g:{GROUP_REGISTRY_LABEL} {{group_id: $group_id}})
        ON CREATE SET 
            g.created_at = datetime(),
            g.creator = $creator,
            g.description = $description,
            g.name = $group_id,
            g.uuid = $uuid
        ON MATCH SET 
            g.updated_at = datetime(),
            g.description = $description,
            g.uuid = COALESCE(g.uuid, $uuid)
        MERGE (root)-[:CONTAINS]->(g)
        """
        
        # Generate a UUID for the group if not provided in metadata
        from uuid import uuid4
        group_uuid = metadata.get("uuid", str(uuid4())) if metadata else str(uuid4())
        
        # Add metadata if provided
        if metadata:
            metadata_parts = []
            params = {
                "root_name": GROUP_REGISTRY_ROOT_NAME,
                "group_id": group_id,
                "description": description,
                "creator": creator,
                "uuid": group_uuid,
            }
            
            for key, value in metadata.items():
                safe_key = key.replace('-', '_')
                metadata_parts.append(f"g.{safe_key} = ${safe_key}")
                params[safe_key] = value
                
            if metadata_parts:
                query += ", " + ", ".join(metadata_parts)
                
            await self.driver.execute_query(query, params)
        else:
            await self.driver.execute_query(
                query,
                {
                    "root_name": GROUP_REGISTRY_ROOT_NAME,
                    "group_id": group_id,
                    "description": description,
                    "creator": creator,
                    "uuid": group_uuid,
                }
            )
            
        logger.info(f"Registered group: {group_id}")
        
        # Return the group info
        return await self.get_group(group_id)
        
    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific group."""
        # Ensure registry is initialized
        await self.initialize()
        
        result = await self.driver.execute_query(
            f"""
            MATCH (root:{GROUP_REGISTRY_ROOT_LABEL} {{name: $root_name}})-[:CONTAINS]->(g:{GROUP_REGISTRY_LABEL} {{group_id: $group_id}})
            RETURN g
            """,
            {"root_name": GROUP_REGISTRY_ROOT_NAME, "group_id": group_id}
        )
        
        if not result[0]:
            return None
            
        # Convert Neo4j node to dict
        node = result[0][0]["g"]
        group_info = dict(node.items())
        
        # Add usage stats
        group_info["usage_stats"] = await self._get_group_usage_stats(group_id)
        
        return group_info
        
    async def list_groups(self, include_protected: bool = False) -> List[Dict[str, Any]]:
        """List all registered groups."""
        # Ensure registry is initialized
        await self.initialize()
        
        query = f"""
        MATCH (root:{GROUP_REGISTRY_ROOT_LABEL} {{name: $root_name}})-[:CONTAINS]->(g:{GROUP_REGISTRY_LABEL})
        """
        
        if not include_protected:
            query += " WHERE NOT g.group_id IN $protected_groups"
            
        query += " RETURN g ORDER BY g.group_id"
        
        result = await self.driver.execute_query(
            query,
            {"root_name": GROUP_REGISTRY_ROOT_NAME, "protected_groups": PROTECTED_GROUPS}
        )
        
        groups = []
        for record in result[0]:
            node = record["g"]
            group_info = dict(node.items())
            groups.append(group_info)
            
        # Add usage stats for each group
        for group in groups:
            group["usage_stats"] = await self._get_group_usage_stats(group["group_id"])
            
        return groups
        
    async def delete_group(self, group_id: str) -> bool:
        """Delete a group from the registry (not the content)."""
        # Ensure registry is initialized
        await self.initialize()
        
        if self.is_protected_group(group_id):
            raise ValueError(f"Cannot delete protected group: {group_id}")
            
        result = await self.driver.execute_query(
            f"""
            MATCH (root:{GROUP_REGISTRY_ROOT_LABEL} {{name: $root_name}})-[r:CONTAINS]->(g:{GROUP_REGISTRY_LABEL} {{group_id: $group_id}})
            DELETE r, g
            RETURN count(g) as deleted
            """,
            {"root_name": GROUP_REGISTRY_ROOT_NAME, "group_id": group_id}
        )
        
        deleted = result[0][0]["deleted"]
        return deleted > 0
        
    async def _get_group_usage_stats(self, group_id: str) -> Dict[str, int]:
        """Get usage statistics for a group."""
        # Ensure registry is initialized
        await self.initialize()
        
        # Count episodic nodes
        episodes_result = await self.driver.execute_query(
            """
            MATCH (e:Episodic {group_id: $group_id})
            RETURN count(e) as episode_count
            """,
            {"group_id": group_id}
        )
        
        # Count entity nodes
        entities_result = await self.driver.execute_query(
            """
            MATCH (n:Entity {group_id: $group_id})
            RETURN count(n) as entity_count
            """,
            {"group_id": group_id}
        )
        
        # Count entity edges
        edges_result = await self.driver.execute_query(
            """
            MATCH ()-[r:ENTITY_EDGE]->()
            WHERE r.group_id = $group_id
            RETURN count(r) as edge_count
            """,
            {"group_id": group_id}
        )
        
        # Get last activity timestamp
        last_activity_result = await self.driver.execute_query(
            """
            MATCH (e:Episodic {group_id: $group_id})
            RETURN max(e.created_at) as last_activity
            """,
            {"group_id": group_id}
        )
        
        episode_count = episodes_result[0][0]["episode_count"] if episodes_result[0] else 0
        entity_count = entities_result[0][0]["entity_count"] if entities_result[0] else 0
        edge_count = edges_result[0][0]["edge_count"] if edges_result[0] else 0
        
        stats = {
            "episode_count": episode_count,
            "entity_count": entity_count,
            "edge_count": edge_count,
            "total_nodes": episode_count + entity_count,
        }
        
        # Add last activity if available
        if last_activity_result[0] and last_activity_result[0][0]["last_activity"]:
            stats["last_activity"] = last_activity_result[0][0]["last_activity"]
            
        return stats
    
    def is_protected_group(self, group_id: str) -> bool:
        """Check if a group is protected."""
        # Note: This is a synchronous method, so we can't call initialize() here
        return group_id in PROTECTED_GROUPS
    
    def _is_valid_group_id(self, group_id: str) -> bool:
        """
        Validate group_id format.
        
        Rules:
        - Must be at least 3 characters
        - Can only contain alphanumeric characters, underscores, and hyphens
        - Must start with a letter
        """
        if not group_id or len(group_id) < 3:
            return False
            
        if not group_id[0].isalpha():
            return False
            
        return all(c.isalnum() or c in "_-" for c in group_id)
