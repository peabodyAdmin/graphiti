# Graphiti Group ID Management System - Revised Implementation Plan

## 🎯 Project Overview

This implementation plan provides a comprehensive approach for upgrading the Graphiti Group ID Management System to enforce secure group_id selection through a two-step process. This system will replace direct group_id specification with a recommendation-based workflow to prevent misplacement of data and ensure proper user input.

## 🔑 Key Architecture Changes

- Replace direct group_id specification in `add_episode` with a recommendation system
- Maintain the existing per-group queue architecture while adding a pending episodes system
- Implement content similarity search using existing Neo4j embedding infrastructure
- Create a new continuation function for finalizing group_id selection
- Add a formal group registry system for tracking group descriptions and metadata
- Ensure proper validation and security throughout the workflow

## 📋 MCP Tools Registration Checklist
- **Modified tools**:
  - `add_episode` (modify to support two-step workflow)
- **New tools**:
  - `continue_episode_ingestion` (for finalizing group_id selection)
  - `list_group_registry` (to display available groups)
  - `register_group` (to register new groups with descriptions)
- **Existing tools to keep unchanged**:
  - All search and query tools
  - All telemetry tools
  - All administration tools

## 📝 Step-by-Step Implementation Plan

### 1. Create Group Registry System

The first step is to implement a formal group registry to track metadata about each group in Neo4j:

```python
# group_registry.py

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)

# Constants
PROTECTED_GROUPS = ['system', 'graphiti_logs', 'admin', 'graphiti_system']
GROUP_REGISTRY_LABEL = 'GroupRegistry'

class GroupRegistry:
    """Manage the group registry in Neo4j."""
    
    def __init__(self, driver: AsyncDriver):
        """Initialize with a Neo4j driver."""
        self.driver = driver
        
    async def initialize(self):
        """Ensure registry indices and constraints exist."""
        # Create constraints for uniqueness
        await self.driver.execute_query(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (g:{GROUP_REGISTRY_LABEL}) REQUIRE g.group_id IS UNIQUE"
        )
        logger.info("Group registry initialized")
        
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
        # Validate group_id
        if not self._is_valid_group_id(group_id):
            raise ValueError(f"Invalid group_id format: {group_id}")
            
        if self.is_protected_group(group_id):
            raise ValueError(f"Cannot modify protected group: {group_id}")
            
        # Create or update group in registry
        query = f"""
        MERGE (g:{GROUP_REGISTRY_LABEL} {{group_id: $group_id}})
        ON CREATE SET 
            g.created_at = datetime(),
            g.creator = $creator,
            g.description = $description
        ON MATCH SET 
            g.updated_at = datetime(),
            g.description = $description
        """
        
        # Add metadata if provided
        if metadata:
            metadata_parts = []
            params = {
                "group_id": group_id,
                "description": description,
                "creator": creator,
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
                    "group_id": group_id,
                    "description": description,
                    "creator": creator,
                }
            )
            
        logger.info(f"Registered group: {group_id}")
        
        # Return the group info
        return await self.get_group(group_id)
        
    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific group."""
        result = await self.driver.execute_query(
            f"""
            MATCH (g:{GROUP_REGISTRY_LABEL} {{group_id: $group_id}})
            RETURN g
            """,
            {"group_id": group_id}
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
        query = f"MATCH (g:{GROUP_REGISTRY_LABEL})"
        
        if not include_protected:
            query += " WHERE NOT g.group_id IN $protected_groups"
            
        query += " RETURN g ORDER BY g.group_id"
        
        result = await self.driver.execute_query(
            query,
            {"protected_groups": PROTECTED_GROUPS}
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
        if self.is_protected_group(group_id):
            raise ValueError(f"Cannot delete protected group: {group_id}")
            
        result = await self.driver.execute_query(
            f"""
            MATCH (g:{GROUP_REGISTRY_LABEL} {{group_id: $group_id}})
            DELETE g
            RETURN count(g) as deleted
            """,
            {"group_id": group_id}
        )
        
        deleted = result[0][0]["deleted"]
        return deleted > 0
        
    async def _get_group_usage_stats(self, group_id: str) -> Dict[str, int]:
        """Get usage statistics for a group."""
        # Count episodic nodes
        episodes_result = await self.driver.execute_query(
            """
            MATCH (e:Episodic {group_id: $group_id})
            RETURN count(e) as episode_count
            """,
            {"group_id": group_id}
        )
        
        episode_count = episodes_result[0][0]["episode_count"] if episodes_result[0] else 0
        
        # Count entity nodes
        entities_result = await self.driver.execute_query(
            """
            MATCH (n:Entity {group_id: $group_id})
            RETURN count(n) as entity_count
            """,
            {"group_id": group_id}
        )
        
        entity_count = entities_result[0][0]["entity_count"] if entities_result[0] else 0
        
        # Return stats
        return {
            "episode_count": episode_count,
            "entity_count": entity_count,
            "total_nodes": episode_count + entity_count
        }
    
    @staticmethod
    def _is_valid_group_id(group_id: str) -> bool:
        """Check if group_id has valid format."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', group_id))
        
    @staticmethod
    def is_protected_group(group_id: str) -> bool:
        """Check if this is a protected system group."""
        return group_id.lower() in PROTECTED_GROUPS
```

This implementation provides:
1. A formal registry to track group metadata
2. Methods to manage, query, and validate groups
3. Usage statistics for each group
4. Protection for system-reserved groups

### 2. Implement Pending Episodes Storage

Next, create a system to temporarily store pending episodes while waiting for group_id confirmation:

```python
# pending_episodes.py

import asyncio
import logging
import uuid
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, TypedDict

logger = logging.getLogger(__name__)

# Type definitions
class PendingEpisode(TypedDict):
    episode_data: Dict[str, Any]
    created_at: float  # timestamp
    expires_at: float  # timestamp
    suggestions: List[Dict[str, Any]]  # group_id suggestions

class PendingEpisodesStorage:
    """Storage system for pending episodes awaiting group_id confirmation."""
    
    def __init__(self, expiration_hours: int = 24):
        """Initialize the pending episodes storage.
        
        Args:
            expiration_hours: Number of hours before pending episodes expire
        """
        self._storage: Dict[str, PendingEpisode] = {}
        self._lock = asyncio.Lock()
        self.expiration_seconds = expiration_hours * 3600
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Initialized pending episodes storage with {expiration_hours}h expiration")
        
    async def store(self, episode_data: Dict[str, Any], 
                    suggestions: List[Dict[str, Any]]) -> str:
        """Store an episode pending group_id confirmation.
        
        Args:
            episode_data: Complete episode data dictionary
            suggestions: List of group_id suggestions with confidence scores
            
        Returns:
            String ID for retrieving the pending episode
        """
        pending_id = str(uuid.uuid4())
        now = time.time()
        
        pending_episode = {
            "episode_data": episode_data,
            "created_at": now,
            "expires_at": now + self.expiration_seconds,
            "suggestions": suggestions
        }
        
        async with self._lock:
            self._storage[pending_id] = pending_episode
            
        logger.debug(f"Stored pending episode {pending_id} for '{episode_data.get('name')}'")
        return pending_id
        
    async def retrieve(self, pending_id: str) -> Optional[PendingEpisode]:
        """Retrieve a pending episode by ID.
        
        Args:
            pending_id: The ID of the pending episode
            
        Returns:
            The pending episode or None if not found/expired
        """
        async with self._lock:
            if pending_id not in self._storage:
                return None
                
            pending = self._storage[pending_id]
            
            # Check if expired
            if time.time() > pending["expires_at"]:
                del self._storage[pending_id]
                logger.debug(f"Pending episode {pending_id} expired during retrieval")
                return None
                
            return pending
            
    async def remove(self, pending_id: str) -> bool:
        """Remove a pending episode.
        
        Args:
            pending_id: The ID of the pending episode
            
        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if pending_id in self._storage:
                del self._storage[pending_id]
                logger.debug(f"Removed pending episode {pending_id}")
                return True
            return False
            
    async def cleanup_expired(self) -> int:
        """Remove all expired pending episodes.
        
        Returns:
            Number of expired episodes that were removed
        """
        now = time.time()
        to_remove = []
        
        async with self._lock:
            for pending_id, pending in self._storage.items():
                if now > pending["expires_at"]:
                    to_remove.append(pending_id)
                    
            for pending_id in to_remove:
                del self._storage[pending_id]
                
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} expired pending episodes")
                
        return len(to_remove)
        
    async def _cleanup_loop(self):
        """Background task that periodically cleans up expired episodes."""
        try:
            while True:
                await asyncio.sleep(3600)  # Run hourly
                await self.cleanup_expired()
        except asyncio.CancelledError:
            logger.info("Pending episodes cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in pending episodes cleanup task: {e}")
            
    async def shutdown(self):
        """Clean up resources before shutdown."""
        if not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
```

This implementation:
1. Creates a thread-safe storage mechanism for pending episodes
2. Implements automatic expiration after a configurable time
3. Includes a background cleanup task to remove expired episodes
4. Provides proper cleanup on shutdown

### 3. Implement Episode Similarity Search

Next, create a module to implement episode similarity search using the existing embedding infrastructure:

```python
# episode_similarity.py

import logging
import asyncio
import re
from typing import Dict, List, Any, Tuple, Optional, NamedTuple
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.search.search_filters import SearchFilters

logger = logging.getLogger(__name__)

class GroupSuggestion(NamedTuple):
    """A suggested group with confidence score and metadata."""
    group_id: str
    confidence: float
    description: str
    episode_count: int
    
class SimilarityResult(NamedTuple):
    """Results of similarity analysis."""
    suggestions: List[GroupSuggestion]
    auto_assign: bool = False
    top_group_id: Optional[str] = None
    top_confidence: float = 0.0
    new_group_suggestion: Optional[str] = None

async def find_similar_episodes(
    graphiti: Graphiti,
    name: str,
    content: str,
    confidence_threshold: float = 0.85,
    max_results: int = 10
) -> SimilarityResult:
    """Find similar episodes across all groups and suggest appropriate group_id.
    
    This function leverages existing embeddings in Neo4j to find similar content,
    then aggregates results by group to provide group suggestions.
    
    Args:
        graphiti: Graphiti client
        name: Episode name
        content: Episode content
        confidence_threshold: Threshold for auto-assignment
        max_results: Maximum episodes to search
        
    Returns:
        SimilarityResult with group suggestions
    """
    # Create embedding for combined content
    combined_text = f"{name}\n\n{content}"
    embedder = graphiti.embedder
    
    if not embedder:
        logger.warning("No embedder available for similarity search")
        return SimilarityResult(suggestions=[])
    
    try:
        # Get embedding for the content
        # We'll leverage the same embedder used for all other embeddings
        embedding = await embedder.get_embeddings([combined_text])
        embedding_vector = embedding[0] if embedding else []
        
        if not embedding_vector:
            logger.warning("Failed to generate embedding for content")
            return SimilarityResult(suggestions=[])
            
        # Use Neo4j's vector search to find similar episodes
        # This leverages existing indices and vector comparisons
        result = await graphiti.driver.execute_query(
            """
            MATCH (e:Episodic)
            WHERE e.name_embedding IS NOT NULL
            WITH e, vector.similarity.cosine(e.name_embedding, $embedding) AS score
            WHERE score > 0.6
            RETURN 
                e.name AS name,
                e.group_id AS group_id,
                score AS similarity_score, 
                e.created_at AS created_at
            ORDER BY similarity_score DESC
            LIMIT $limit
            """,
            {
                "embedding": embedding_vector,
                "limit": max_results
            }
        )
        
        if not result[0]:
            # No similar episodes found
            suggested_name = generate_group_id_suggestion(name, content)
            return SimilarityResult(
                suggestions=[],
                new_group_suggestion=suggested_name
            )
            
        # Group results by group_id and calculate confidence
        group_scores: Dict[str, List[Tuple[float, Dict[str, Any]]]] = {}
        
        for record in result[0]:
            group_id = record["group_id"]
            score = record["similarity_score"]
            episode_info = {
                "name": record["name"],
                "created_at": record["created_at"],
                "similarity_score": score
            }
            
            if group_id not in group_scores:
                group_scores[group_id] = []
                
            group_scores[group_id].append((score, episode_info))
            
        # Now get descriptions for each group from the registry
        from mcp_server.services.group_registry import GroupRegistry
        registry = GroupRegistry(graphiti.driver)
        
        suggestions = []
        for group_id, scores_and_episodes in group_scores.items():
            # Calculate weighted average confidence
            scores = [score for score, _ in scores_and_episodes]
            avg_confidence = sum(scores) / len(scores)
            
            # Get group info
            group_info = await registry.get_group(group_id)
            description = group_info.get("description") if group_info else f"Group containing {scores_and_episodes[0][1]['name']}"
            
            suggestions.append(GroupSuggestion(
                group_id=group_id,
                confidence=avg_confidence,
                description=description,
                episode_count=len(scores_and_episodes)
            ))
            
        # Sort suggestions by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        # Generate a new group suggestion
        new_group_suggestion = generate_group_id_suggestion(name, content)
        
        # Check if top suggestion exceeds threshold
        if suggestions and suggestions[0].confidence >= confidence_threshold:
            return SimilarityResult(
                suggestions=suggestions,
                auto_assign=True,
                top_group_id=suggestions[0].group_id,
                top_confidence=suggestions[0].confidence,
                new_group_suggestion=new_group_suggestion
            )
        else:
            return SimilarityResult(
                suggestions=suggestions,
                auto_assign=False,
                new_group_suggestion=new_group_suggestion
            )
    
    except Exception as e:
        logger.error(f"Error in similarity search: {e}", exc_info=True)
        return SimilarityResult(suggestions=[])

def generate_group_id_suggestion(name: str, content: str) -> str:
    """Generate a suggested group ID based on episode content."""
    # Extract first few words from the name for a reasonable group_id
    words = re.findall(r'\w+', name.lower())[:3]
    
    if not words:
        # Fall back to first few words of content
        words = re.findall(r'\w+', content.lower())[:3]
        
    if not words:
        return "new-content-group"
        
    return "-".join(words[:3])
```

This implementation:
1. Uses the existing embedding infrastructure
2. Leverages Neo4j's vector operations for similarity comparison
3. Aggregates results by group_id with confidence scores
4. Integrates with the group registry for metadata
5. Includes a reasonable group_id suggestion generator

### 4. Modify the add_episode Function

Update the existing add_episode function to support the two-step workflow:

```python
# New response type for pending episodes
class PendingResponse(TypedDict):
    message: str
    pending_episode_id: str
    suggested_group_ids: List[Dict[str, Any]]
    new_group_suggestion: str
    requires_selection: bool

@mcp.tool()
async def add_episode(
    name: str,
    episode_body: str,
    group_id: str = None,  # Changed to optional
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
    tags: list[str] | None = None,
    labels: list[str] | None = None,
) -> SuccessResponse | ErrorResponse | PendingResponse:
    """Add an episode to the Graphiti knowledge graph.
    
    This function implements a two-step workflow to ensure proper group_id selection:
    1. If group_id is provided, it validates the group_id and adds the episode directly
    2. If group_id is not provided, it analyzes the content to suggest appropriate groups
       and returns a pending_episode_id for continuation
    
    Args:
        name: Name of the episode
        episode_body: Content of the episode
        group_id: Optional group_id. If not provided, system will suggest groups.
        source: Source type ('text', 'json', 'message')
        source_description: Description of the source
        uuid: Optional UUID for the episode
        tags: List of tags for the episode
        labels: List of labels for the episode
        
    Returns:
        SuccessResponse: If episode was added directly
        PendingResponse: If user needs to select a group_id
        ErrorResponse: If an error occurred
    """
    global graphiti_client, episode_queues, queue_workers
    
    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}
        
    try:
        # Map string source to EpisodeType enum
        source_type = EpisodeType.text
        if source.lower() == 'message':
            source_type = EpisodeType.message
        elif source.lower() == 'json':
            source_type = EpisodeType.json
            
        # Prepare the episode data dictionary
        episode_data = {
            "name": name,
            "episode_body": episode_body,
            "source": source_type,
            "source_description": source_description,
            "uuid": uuid,
            "reference_time": datetime.now(timezone.utc),
            "entity_types": ENTITY_TYPES if config.use_custom_entities else {},
            "update_communities": True,
            "tags": tags or [],
            "labels": labels or [],
        }
        
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None, 'graphiti_client should not be None here'
        
        # Case 1: Group ID is provided
        if group_id:
            # Validate the group_id
            from mcp_server.services.group_registry import GroupRegistry
            registry = GroupRegistry(graphiti_client.driver)
            
            # Check if group_id is valid format
            if not registry._is_valid_group_id(group_id):
                return {'error': f'Invalid group_id format: {group_id}. Only alphanumeric characters, hyphens, and underscores are allowed.'}
                
            # Check if it's a protected group
            if registry.is_protected_group(group_id):
                return {'error': f'Cannot use protected group_id: {group_id}'}
                
            # Use the provided group_id
            group_id_str = str(group_id)
            
            # Add the group_id to episode data
            episode_data["group_id"] = group_id_str
            
            # Ensure the group exists in registry - auto-create if not
            group_info = await registry.get_group(group_id_str)
            if not group_info:
                # Register the group with a basic description if not found
                try:
                    await registry.register_group(
                        group_id=group_id_str,
                        description=f"Group created for {name}",
                        creator=f"add_episode:{datetime.now(timezone.utc).isoformat()}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to auto-register group {group_id_str}: {e}")
                    # Continue anyway - this is just a convenience feature
            
            # Process the episode through the existing queue system
            # Initialize queue for this group_id if it doesn't exist
            if group_id_str not in episode_queues:
                episode_queues[group_id_str] = asyncio.Queue()
                
            # Add the episode data to the queue
            await episode_queues[group_id_str].put(episode_data)
            
            # Start a worker for this queue if one isn't already running
            if not queue_workers.get(group_id_str, False):
                asyncio.create_task(process_episode_queue(group_id_str))
                
            # Return immediate success
            return {
                'message': f"Episode '{name}' queued for processing in group '{group_id_str}' (position: {episode_queues[group_id_str].qsize()})"
            }
            
        # Case 2: No group_id provided - analyze content and suggest groups
        else:
            # Import similarity search
            from mcp_server.services.episode_similarity import find_similar_episodes
            
            # Find similar episodes and get group suggestions
            similarity_result = await find_similar_episodes(
                graphiti=graphiti_client,
                name=name,
                content=episode_body,
                confidence_threshold=0.85  # Configurable threshold
            )
            
            # If we have high confidence for auto-assignment
            if similarity_result.auto_assign and similarity_result.top_group_id:
                group_id_str = similarity_result.top_group_id
                
                # Add the determined group_id to the episode data
                episode_data["group_id"] = group_id_str
                
                # Initialize queue for this group_id if it doesn't exist
                if group_id_str not in episode_queues:
                    episode_queues[group_id_str] = asyncio.Queue()
                    
                # Add the episode data to the queue
                await episode_queues[group_id_str].put(episode_data)
                
                # Start a worker for this queue if one isn't already running
                if not queue_workers.get(group_id_str, False):
                    asyncio.create_task(process_episode_queue(group_id_str))
                
                # Return success with auto-assignment info
                return {
                    'message': f"Episode '{name}' auto-assigned to group '{group_id_str}' (confidence: {similarity_result.top_confidence:.2f}) and queued for processing"
                }
            else:
                # We need user input for group selection
                # Store the episode in pending storage
                from mcp_server.services.pending_episodes import pending_episodes_storage
                
                # Format suggestions for the response
                suggestions = []
                for suggestion in similarity_result.suggestions:
                    suggestions.append({
                        "group_id": suggestion.group_id,
                        "confidence": suggestion.confidence,
                        "description": suggestion.description,
                        "episode_count": suggestion.episode_count
                    })
                
                # Store episode in pending storage
                pending_id = await pending_episodes_storage.store(
                    episode_data=episode_data,
                    suggestions=suggestions
                )
                
                # Return pending response
                return {
                    "message": "Group ID determination requires user input. Please select from suggestions or create a new group.",
                    "pending_episode_id": pending_id,
                    "suggested_group_ids": suggestions,
                    "new_group_suggestion": similarity_result.new_group_suggestion or "new-content-group",
                    "requires_selection": True
                }
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error in add_episode: {error_msg}', exc_info=True)
        return {'error': f'Error processing episode: {error_msg}'}
```

This modified implementation:
1. Makes group_id optional (backward compatible but encourages the new flow)
2. Adds validation when group_id is directly provided
3. Leverages the similarity search when no group_id is provided
4. Either auto-assigns with high confidence or stores as pending
5. Returns appropriate response types for each case 

### 5. Implement the continue_episode_ingestion Function

Add the new continuation function to complete the two-step workflow:

```python
@mcp.tool()
async def continue_episode_ingestion(
    pending_episode_id: str,
    selected_group_id: str,
    is_new_group: bool = False,
    group_description: str = None,
) -> SuccessResponse | ErrorResponse:
    """Continue the ingestion of a pending episode with selected group_id.
    
    This function completes the two-step episode ingestion workflow:
    1. Validates the selected group_id
    2. Retrieves the pending episode from storage
    3. Processes the episode with the selected group_id
    
    Args:
        pending_episode_id: ID of the pending episode from add_episode
        selected_group_id: User's selected group_id
        is_new_group: True if creating a new group
        group_description: Description for the new group (required if is_new_group=True)
        
    Returns:
        SuccessResponse: If processing succeeded
        ErrorResponse: If an error occurred
    """
    global graphiti_client, episode_queues, queue_workers
    
    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}
        
    try:
        # Access the pending episodes storage
        from mcp_server.services.pending_episodes import pending_episodes_storage
        
        # Get the group registry
        from mcp_server.services.group_registry import GroupRegistry
        registry = GroupRegistry(graphiti_client.driver)
        
        # Validate the selected group_id
        if not registry._is_valid_group_id(selected_group_id):
            return {'error': f'Invalid group_id format: {selected_group_id}. Only alphanumeric characters, hyphens, and underscores are allowed.'}
            
        # Check if it's a protected group
        if registry.is_protected_group(selected_group_id):
            return {'error': f'Cannot use protected group_id: {selected_group_id}'}
            
        # Retrieve pending episode
        pending = await pending_episodes_storage.retrieve(pending_episode_id)
        if not pending:
            return {'error': 'Pending episode not found or expired. Please submit the episode again.'}
            
        # Extract the episode data
        episode_data = pending["episode_data"]
        episode_name = episode_data.get("name", "Unknown episode")
        
        # Handle group registration
        if is_new_group:
            # Require description for new groups
            if not group_description:
                return {'error': 'Group description is required when creating a new group'}
                
            # Register the new group
            try:
                await registry.register_group(
                    group_id=selected_group_id,
                    description=group_description,
                    creator=f"continue_episode_ingestion:{datetime.now(timezone.utc).isoformat()}"
                )
                logger.info(f"Registered new group: {selected_group_id}")
            except ValueError as e:
                return {'error': f'Failed to register group: {str(e)}'}
                
        # Add the selected group_id to the episode data
        episode_data["group_id"] = selected_group_id
        
        # Process the episode through the existing queue system
        # Initialize queue for this group_id if it doesn't exist
        if selected_group_id not in episode_queues:
            episode_queues[selected_group_id] = asyncio.Queue()
            
        # Add the episode data to the queue
        await episode_queues[selected_group_id].put(episode_data)
        
        # Start a worker for this queue if one isn't already running
        if not queue_workers.get(selected_group_id, False):
            asyncio.create_task(process_episode_queue(selected_group_id))
            
        # Remove the pending episode from storage
        await pending_episodes_storage.remove(pending_episode_id)
        
        # Return success
        return {
            'message': f"Episode '{episode_name}' queued for processing in group '{selected_group_id}' (position: {episode_queues[selected_group_id].qsize()})"
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error in continue_episode_ingestion: {error_msg}', exc_info=True)
        return {'error': f'Error continuing episode ingestion: {error_msg}'}

### 6. Implement Group Registry MCP Tools

Add tools to interact with the group registry:

```python
@mcp.tool()
async def list_group_registry(
    include_protected: bool = False,
    include_stats: bool = True,
) -> Dict[str, Any] | ErrorResponse:
    """List all registered groups in the system.
    
    This tool provides visibility into available groups for organizing content.
    
    Args:
        include_protected: Whether to include system-protected groups
        include_stats: Whether to include usage statistics
        
    Returns:
        Dictionary with group information or error response
    """
    global graphiti_client
    
    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}
        
    try:
        from mcp_server.services.group_registry import GroupRegistry
        registry = GroupRegistry(graphiti_client.driver)
        
        groups = await registry.list_groups(include_protected=include_protected)
        
        # If not including stats, remove them
        if not include_stats:
            for group in groups:
                if "usage_stats" in group:
                    del group["usage_stats"]
                    
        return {
            'message': f'Retrieved {len(groups)} groups',
            'groups': groups
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error listing group registry: {error_msg}', exc_info=True)
        return {'error': f'Error listing group registry: {error_msg}'}

@mcp.tool()
async def register_group(
    group_id: str,
    description: str,
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any] | ErrorResponse:
    """Register a new group or update an existing group.
    
    This tool creates or updates entries in the group registry.
    
    Args:
        group_id: Unique ID for the group (alphanumeric with hyphens/underscores)
        description: Human-readable description of the group's purpose
        metadata: Optional dictionary of additional metadata to store
        
    Returns:
        Group information or error response
    """
    global graphiti_client
    
    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}
        
    try:
        from mcp_server.services.group_registry import GroupRegistry
        registry = GroupRegistry(graphiti_client.driver)
        
        try:
            group_info = await registry.register_group(
                group_id=group_id,
                description=description,
                creator=f"register_group:{datetime.now(timezone.utc).isoformat()}",
                metadata=metadata
            )
            
            return {
                'message': f"Successfully registered group '{group_id}'",
                'group': group_info
            }
            
        except ValueError as e:
            return {'error': str(e)}
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error registering group: {error_msg}', exc_info=True)
        return {'error': f'Error registering group: {error_msg}'}
```

### 7. Initialize Services in Server Startup

Finally, modify the server initialization to set up the new services:

```python
# Global instances of services
group_registry = None
pending_episodes_storage = None

async def initialize_server() -> tuple[FastMCP, MCPConfig]:
    """Parse CLI arguments and initialize the Graphiti server configuration."""
    global mcp, config, telemetry_client, mcp_config, group_registry, pending_episodes_storage
    
    # [Existing initialization code...]
    
    # Initialize the Group Registry
    from mcp_server.services.group_registry import GroupRegistry
    group_registry = GroupRegistry(graphiti_client.driver)
    await group_registry.initialize()
    logger.info("Group registry initialized")
    
    # Initialize the Pending Episodes Storage
    from mcp_server.services.pending_episodes import PendingEpisodesStorage
    pending_episodes_storage = PendingEpisodesStorage(expiration_hours=24)
    logger.info("Pending episodes storage initialized")
    
    # Register modified and new tools
    logger.info("Registering Group ID Management tools")
    mcp.tool()(add_episode)  # Modified
    mcp.tool()(continue_episode_ingestion)  # New
    mcp.tool()(list_group_registry)  # New
    mcp.tool()(register_group)  # New
    
    # [Rest of existing initialization...]
    
    return mcp, mcp_config
```

## 📊 Migration Plan

To ensure a smooth transition to the new system, the following migration steps are recommended:

1. **Deploy with Backward Compatibility**: The modified `add_episode` function accepts both direct group_id specification and the new workflow. This allows existing clients to continue working during the transition.

2. **Auto-Populate Group Registry**: When the system starts up, scan existing groups and populate the registry with basic information:

```python
async def populate_initial_registry():
    """Scan the database for existing groups and populate the registry."""
    # Query for all distinct group_ids
    result = await graphiti_client.driver.execute_query(
        """
        MATCH (n)
        WHERE n.group_id IS NOT NULL
        RETURN DISTINCT n.group_id AS group_id, count(n) AS node_count
        """
    )
    
    for record in result[0]:
        group_id = record["group_id"]
        node_count = record["node_count"]
        
        # Skip if already in registry
        group_info = await group_registry.get_group(group_id)
        if group_info:
            continue
            
        # Skip protected groups (they'll be registered separately)
        if group_registry.is_protected_group(group_id):
            continue
            
        # Register with basic info
        try:
            await group_registry.register_group(
                group_id=group_id,
                description=f"Auto-registered group with {node_count} nodes",
                creator="migration"
            )
            logger.info(f"Auto-registered existing group: {group_id}")
        except Exception as e:
            logger.warning(f"Failed to auto-register group {group_id}: {e}")
```

3. **Client Communication**: Advise clients of the new workflow through notifications and documentation updates.

## 🧪 Testing Strategy

The implementation should be thoroughly tested for:

1. **Backward Compatibility**:
   - Verify existing clients can still use direct group_id specification
   - Ensure all existing functionality continues to work

2. **New Workflow Testing**:
   - Test content similarity matching with various confidence levels
   - Verify proper handling of pending episodes and continuation
   - Test expiration and cleanup of pending episodes

3. **Security Validation**:
   - Ensure protected groups remain protected
   - Verify proper validation of group_id formats

4. **Edge Cases**:
   - Test with very large episodes
   - Test concurrent ingestion requests
   - Test recovery from failures at various stages

## 🛡️ Security Considerations

This implementation provides several security improvements:

1. **Protected Group Enforcement**: Systematic protection of system-critical groups
2. **Formal Validation**: Consistent validation of group_id formats and permissions
3. **Audit Trail**: Registry entries include creation metadata for accountability
4. **Expiring Pending Episodes**: Automatic cleanup prevents lingering sensitive data

## 📝 Documentation Updates

Client documentation should be updated to reflect the new workflow:

```markdown
# Using the Graphiti Episode Ingestion API

## Two-Step Ingestion Workflow

The Graphiti API now supports a two-step episode ingestion workflow that helps ensure proper group_id selection:

### Step 1: Submit the episode content

```python
response = await client.add_episode(
    name="My Document",
    episode_body="This is the content of my document...",
    source="text",
    source_description="User-provided content"
)
```

### Step 2: Check response type

The response will be one of two types:

1. **Success Response** (auto-assigned):
```python
{
    "message": "Episode 'My Document' auto-assigned to group 'existing-group' (confidence: 0.92) and queued for processing"
}
```

2. **Pending Response** (needs selection):
```python
{
    "message": "Group ID determination requires user input",
    "pending_episode_id": "1234-5678-90ab-cdef",
    "suggested_group_ids": [
        {
            "group_id": "similar-group-1",
            "confidence": 0.75,
            "description": "Group containing similar content",
            "episode_count": 42
        },
        ...
    ],
    "new_group_suggestion": "suggested-new-name",
    "requires_selection": true
}
```

### Step 3: Continue with selection (if needed)

If you received a Pending Response, complete the ingestion:

```python
# Using an existing group
response = await client.continue_episode_ingestion(
    pending_episode_id="1234-5678-90ab-cdef",
    selected_group_id="similar-group-1"
)

# OR creating a new group
response = await client.continue_episode_ingestion(
    pending_episode_id="1234-5678-90ab-cdef",
    selected_group_id="my-new-group",
    is_new_group=True,
    group_description="My custom group for specific content"
)
```

### Backward Compatibility

For existing integrations, you can still provide the group_id directly:

```python
response = await client.add_episode(
    name="My Document",
    episode_body="This is the content...",
    group_id="my-existing-group"  # Direct specification still works
)
```

However, the new workflow is recommended for improved organization and data placement.