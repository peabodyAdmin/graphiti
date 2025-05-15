"""
Pending episodes storage system for the two-step group_id workflow.

This module provides storage for episodes that are awaiting group_id confirmation,
allowing for a secure two-step process for group selection.
"""

import json
import logging
import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, NamedTuple

logger = logging.getLogger(__name__)

class PendingEpisode(NamedTuple):
    """Structure for a pending episode."""
    pending_id: str
    name: str
    episode_body: str
    source: str
    source_description: str
    suggested_group_id: str
    similar_groups: List[Dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    uuid: Optional[str]
    tags: Optional[List[str]]
    labels: Optional[List[str]]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PendingEpisode':
        """Create a PendingEpisode from a dictionary."""
        return cls(
            pending_id=data["pending_id"],
            name=data["name"],
            episode_body=data["episode_body"],
            source=data["source"],
            source_description=data["source_description"],
            suggested_group_id=data["suggested_group_id"],
            similar_groups=data["similar_groups"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            uuid=data.get("uuid"),
            tags=data.get("tags"),
            labels=data.get("labels"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for storage."""
        return {
            "pending_id": self.pending_id,
            "name": self.name,
            "episode_body": self.episode_body,
            "source": self.source,
            "source_description": self.source_description,
            "suggested_group_id": self.suggested_group_id,
            "similar_groups": self.similar_groups,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "uuid": self.uuid,
            "tags": self.tags,
            "labels": self.labels,
        }

class PendingEpisodesStorage:
    """Storage system for pending episodes awaiting group_id confirmation."""
    
    def __init__(self, storage_dir: Optional[str] = None, expiration_hours: int = 24):
        """Initialize the pending episodes storage.
        
        Args:
            storage_dir: Directory to store pending episodes. If None, uses a default.
            expiration_hours: Hours until a pending episode expires
        """
        self.expiration_hours = expiration_hours
        
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            # Default to a 'pending_episodes' directory in the project root
            self.storage_dir = Path(__file__).parent.parent.parent / "pending_episodes"
            
        # Ensure the storage directory exists
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Pending episodes storage initialized at {self.storage_dir}")
    
    def store_pending_episode(
        self,
        name: str,
        episode_body: str,
        source: str,
        source_description: str,
        suggested_group_id: str,
        similar_groups: List[Dict[str, Any]],
        uuid: Optional[str] = None,
        tags: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
    ) -> str:
        """
        Store a pending episode.
        
        Args:
            name: Episode name
            episode_body: Episode content
            source: Source type
            source_description: Description of source
            suggested_group_id: Suggested group ID
            similar_groups: List of similar groups with scores
            uuid: Optional UUID for the episode
            tags: Optional tags for the episode
            labels: Optional labels for the episode
            
        Returns:
            pending_id: ID for retrieving the pending episode
        """
        # Generate a unique ID for this pending episode
        pending_id = str(uuid_module.uuid4())
        
        # Calculate expiration time
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.expiration_hours)
        
        # Create the pending episode
        pending_episode = PendingEpisode(
            pending_id=pending_id,
            name=name,
            episode_body=episode_body,
            source=source,
            source_description=source_description,
            suggested_group_id=suggested_group_id,
            similar_groups=similar_groups,
            created_at=now,
            expires_at=expires_at,
            uuid=uuid,
            tags=tags,
            labels=labels,
        )
        
        # Save to storage
        self._save_pending_episode(pending_episode)
        
        logger.info(f"Stored pending episode with ID: {pending_id}")
        return pending_id
    
    def get_pending_episode(self, pending_id: str) -> Optional[PendingEpisode]:
        """
        Retrieve a pending episode by its ID.
        
        Args:
            pending_id: ID of the pending episode
            
        Returns:
            The pending episode if found and not expired, None otherwise
        """
        file_path = self.storage_dir / f"{pending_id}.json"
        
        if not file_path.exists():
            logger.warning(f"Pending episode not found: {pending_id}")
            return None
            
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                
            pending_episode = PendingEpisode.from_dict(data)
            
            # Check if expired
            if pending_episode.expires_at < datetime.now(timezone.utc):
                logger.warning(f"Pending episode expired: {pending_id}")
                self.delete_pending_episode(pending_id)
                return None
                
            return pending_episode
        except Exception as e:
            logger.error(f"Error retrieving pending episode {pending_id}: {str(e)}")
            return None
    
    def delete_pending_episode(self, pending_id: str) -> bool:
        """
        Delete a pending episode.
        
        Args:
            pending_id: ID of the pending episode
            
        Returns:
            True if deleted successfully, False otherwise
        """
        file_path = self.storage_dir / f"{pending_id}.json"
        
        if not file_path.exists():
            return False
            
        try:
            file_path.unlink()
            logger.info(f"Deleted pending episode: {pending_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting pending episode {pending_id}: {str(e)}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired pending episodes.
        
        Returns:
            Number of expired episodes removed
        """
        count = 0
        now = datetime.now(timezone.utc)
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                expires_at = datetime.fromisoformat(data["expires_at"])
                
                if expires_at < now:
                    file_path.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Error during cleanup of {file_path.name}: {str(e)}")
                
        logger.info(f"Cleaned up {count} expired pending episodes")
        return count
    
    def _save_pending_episode(self, pending_episode: PendingEpisode) -> None:
        """Save a pending episode to storage."""
        file_path = self.storage_dir / f"{pending_episode.pending_id}.json"
        
        with open(file_path, "w") as f:
            json.dump(pending_episode.to_dict(), f, indent=2)
