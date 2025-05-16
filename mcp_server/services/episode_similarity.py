"""
Episode similarity search for group_id suggestions.

This module provides functionality to find similar episodes across all groups
and suggest appropriate group_ids based on content similarity.
"""

import re
import logging
import asyncio
from typing import Dict, List, Any, Tuple, Optional, NamedTuple
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.nodes import EpisodicNode

logger = logging.getLogger(__name__)

# Constants
MIN_SIMILARITY_SCORE = 0.5  # Minimum similarity score to consider
MAX_RESULTS_PER_GROUP = 3   # Maximum number of results per group
MAX_GROUPS = 5              # Maximum number of group suggestions to return

class SimilarityResult(NamedTuple):
    """Result of a similarity search."""
    suggested_group_id: str
    similar_groups: List[Dict[str, Any]]
    similar_episodes: List[Dict[str, Any]]
    auto_assign: bool = False
    confidence: float = 0.0

async def find_similar_episodes(
    graphiti: Graphiti,
    name: str,
    content: str,
    embedder: Optional[EmbedderClient] = None,
    confidence_threshold: float = 0.85,
) -> SimilarityResult:
    """Find similar episodes across all groups and suggest appropriate group_id.
    
    This function leverages existing embeddings in Neo4j to find similar content,
    then aggregates results by group to provide group suggestions.
    
    Args:
        graphiti: Graphiti instance
        name: Episode name
        content: Episode content
        embedder: Optional embedder client (uses graphiti's embedder if None)
        
    Returns:
        SimilarityResult with suggested group_id and similar groups/episodes
    """
    # Use provided embedder or fall back to graphiti's embedder
    embedder = embedder or graphiti.embedder
    
    # Generate embedding for the input content
    embedding = await embedder.create(content)
    
    # Search for similar episodes using a custom vector similarity calculation
    # that doesn't rely on the GDS library
    query = """
    MATCH (e:Episodic)
    WHERE e.embedding IS NOT NULL
    
    // Calculate dot product between vectors
    WITH e, 
         reduce(dot = 0.0, i in range(0, size($embedding)-1) | 
                dot + $embedding[i] * e.embedding[i]) as dotProduct,
         // Calculate magnitudes
         sqrt(reduce(mag1 = 0.0, i in range(0, size($embedding)-1) | 
                mag1 + $embedding[i] * $embedding[i])) as mag1,
         sqrt(reduce(mag2 = 0.0, i in range(0, size(e.embedding)-1) | 
                mag2 + e.embedding[i] * e.embedding[i])) as mag2
    
    // Calculate cosine similarity
    WITH e, 
         CASE 
           WHEN mag1 * mag2 = 0 THEN 0 
           ELSE dotProduct / (mag1 * mag2) 
         END as similarity
    
    WHERE similarity > $min_similarity
    RETURN e, similarity
    ORDER BY similarity DESC
    LIMIT 100
    """
    
    result = await graphiti.driver.execute_query(
        query,
        {
            "embedding": embedding,
            "min_similarity": MIN_SIMILARITY_SCORE
        }
    )
    
    # Process results
    similar_episodes = []
    group_scores = {}  # Aggregate scores by group
    group_episodes = {}  # Track episodes per group
    
    for record in result[0]:
        node = record["e"]
        similarity = record["similarity"]
        
        episode_data = dict(node.items())
        episode_data["similarity"] = similarity
        
        # Extract key information
        group_id = episode_data.get("group_id", "")
        if not group_id:
            continue
            
        # Process any DateTime objects for JSON serialization
        serializable_episode_data = {}
        for key, value in episode_data.items():
            # Convert Neo4j DateTime objects to ISO format strings
            if hasattr(value, "to_native"):
                serializable_episode_data[key] = value.to_native().isoformat()
            else:
                serializable_episode_data[key] = value
                
        # Add to similar episodes list
        similar_episodes.append(serializable_episode_data)
        
        # Track group scores
        if group_id not in group_scores:
            group_scores[group_id] = 0
            group_episodes[group_id] = []
            
        # Add score to group total (weighted by similarity)
        group_scores[group_id] += similarity
        
        # Add to group episodes (limited per group)
        if len(group_episodes[group_id]) < MAX_RESULTS_PER_GROUP:
            # Convert Neo4j DateTime to ISO format string to ensure JSON serialization works
            created_at = episode_data.get("created_at", "")
            if hasattr(created_at, "to_native"):
                created_at = created_at.to_native().isoformat()
                
            group_episodes[group_id].append({
                "name": episode_data.get("name", ""),
                "content": episode_data.get("content", "")[:200] + "...",  # Truncate for brevity
                "similarity": similarity,
                "created_at": created_at,
            })
    
    # Get group descriptions
    group_descriptions = await _get_group_descriptions(graphiti, list(group_scores.keys()))
    
    # Sort groups by score and create result list
    sorted_groups = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
    
    similar_groups = []
    for group_id, score in sorted_groups[:MAX_GROUPS]:
        similar_groups.append({
            "group_id": group_id,
            "score": score,
            "description": group_descriptions.get(group_id, ""),
            "sample_episodes": group_episodes[group_id],
        })
    
    # Generate a suggested group_id
    suggested_group_id = ""
    if similar_groups:
        # Use the highest scoring group
        suggested_group_id = similar_groups[0]["group_id"]
    else:
        # Generate a new group_id based on the content
        suggested_group_id = generate_group_id_suggestion(name, content)
    
    # Determine if we should auto-assign based on confidence
    auto_assign = False
    confidence = 0.0
    
    if similar_groups:
        # Get the confidence score from the top group
        confidence = similar_groups[0]["score"]
        # Auto-assign if confidence exceeds threshold
        auto_assign = confidence >= confidence_threshold
    
    return SimilarityResult(
        suggested_group_id=suggested_group_id,
        similar_groups=similar_groups,
        similar_episodes=similar_episodes[:10],  # Limit to top 10 overall
        auto_assign=auto_assign,
        confidence=confidence
    )

async def _get_group_descriptions(graphiti: Graphiti, group_ids: List[str]) -> Dict[str, str]:
    """Get descriptions for a list of group IDs."""
    # Check if the GroupRegistry and GroupRegistryRoot labels exist
    check_query = """
    CALL db.labels() YIELD label
    WITH collect(label) as labels
    RETURN 
        'GroupRegistry' IN labels AS registry_exists,
        'GroupRegistryRoot' IN labels AS root_exists
    """
    
    check_result = await graphiti.driver.execute_query(check_query)
    registry_exists = check_result[0][0]["registry_exists"] if check_result[0] else False
    root_exists = check_result[0][0]["root_exists"] if check_result[0] else False
    
    if not registry_exists or not root_exists:
        # No registry, return empty descriptions
        return {group_id: "" for group_id in group_ids}
    
    # Query the registry for descriptions using the new structure
    query = """
    MATCH (root:GroupRegistryRoot {name: 'Group Registry'})-[:CONTAINS]->(g:GroupRegistry)
    WHERE g.group_id IN $group_ids
    RETURN g.group_id AS group_id, g.description AS description
    """
    
    result = await graphiti.driver.execute_query(
        query,
        {"group_ids": group_ids}
    )
    
    # Build description dictionary
    descriptions = {}
    for record in result[0]:
        group_id = record["group_id"]
        description = record["description"]
        descriptions[group_id] = description
    
    # Add empty descriptions for missing groups
    for group_id in group_ids:
        if group_id not in descriptions:
            descriptions[group_id] = ""
    
    return descriptions

def generate_group_id_suggestion(name: str, content: str) -> str:
    """Generate a suggested group ID based on episode content."""
    # Extract first few words from the name for a reasonable group_id
    words = re.findall(r'\w+', name.lower())[:3]
    
    if not words:
        # Fallback if name doesn't contain usable words
        return "new_content_group"
        
    # Join with underscores and ensure it starts with a letter
    group_id = '_'.join(words)
    
    # Ensure it starts with a letter
    if not group_id[0].isalpha():
        group_id = "g_" + group_id
        
    # Ensure minimum length
    if len(group_id) < 3:
        group_id += "_group"
        
    return group_id
