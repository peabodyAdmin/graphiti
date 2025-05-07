"""Context management for Graphiti operations.

This module provides a context manager for tracking node and edge state
during graph operations. It ensures that nodes being created in the current
operation are available for edge creation, even before they are committed
to the database.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Node(BaseModel):
    """A node in the graph with its state information."""
    uuid: str
    name: str
    labels: List[str]
    attributes: Dict[str, Any]
    created_at: datetime
    group_id: str
    state: str = "pending"  # pending, committed, failed

class Edge(BaseModel):
    """An edge in the graph with its state information."""
    uuid: str
    source_uuid: str
    target_uuid: str
    relation_type: str
    fact: str
    valid_at: Optional[datetime] = None
    invalid_at: Optional[datetime] = None
    state: str = "pending"  # pending, committed, failed

class GraphContext:
    """Manages state for graph operations.
    
    This class tracks nodes and edges as they move through their lifecycle:
    pending -> committed or failed. It ensures that edge creation can
    reference nodes that are being created in the same transaction.
    """
    
    def __init__(self):
        self.pending_nodes: Dict[str, Node] = {}  # uuid -> Node
        self.committed_nodes: Dict[str, Node] = {}
        self.failed_nodes: Dict[str, Node] = {}
        
        self.pending_edges: Dict[str, Edge] = {}  # uuid -> Edge
        self.committed_edges: Dict[str, Edge] = {}
        self.failed_edges: Dict[str, Edge] = {}
        
        # Track node names for quick lookup
        self.node_names: Dict[str, str] = {}  # name -> uuid
        
        # Track relationships for cycle detection
        self.relationships: Set[tuple[str, str]] = set()  # (source_uuid, target_uuid)
        
    def add_node(self, node: Node) -> None:
        """Add a node to pending state.
        
        Args:
            node: The node to add
            
        Raises:
            ValueError: If node with same UUID already exists
        """
        if node.uuid in self.pending_nodes:
            raise ValueError(f"Node with UUID {node.uuid} already pending")
        if node.uuid in self.committed_nodes:
            raise ValueError(f"Node with UUID {node.uuid} already committed")
            
        self.pending_nodes[node.uuid] = node
        self.node_names[node.name] = node.uuid
        logger.debug(f"Added pending node: {node.name} ({node.uuid})")
        
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to pending state.
        
        Args:
            edge: The edge to add
            
        Raises:
            ValueError: If edge with same UUID exists or creates a cycle
        """
        if edge.uuid in self.pending_edges:
            raise ValueError(f"Edge with UUID {edge.uuid} already pending")
        if edge.uuid in self.committed_edges:
            raise ValueError(f"Edge with UUID {edge.uuid} already committed")
            
        # Check for cycles
        relationship = (edge.source_uuid, edge.target_uuid)
        if relationship in self.relationships:
            raise ValueError(
                f"Edge would create cycle between {edge.source_uuid} and {edge.target_uuid}"
            )
            
        self.pending_edges[edge.uuid] = edge
        self.relationships.add(relationship)
        logger.debug(
            f"Added pending edge: {edge.relation_type} from {edge.source_uuid} to {edge.target_uuid}"
        )
        
    def get_node_by_name(self, name: str) -> Optional[Node]:
        """Get a node by its name from either pending or committed nodes."""
        uuid = self.node_names.get(name)
        if uuid:
            return (
                self.pending_nodes.get(uuid) or 
                self.committed_nodes.get(uuid)
            )
        return None
        
    def get_node_by_uuid(self, uuid: str) -> Optional[Node]:
        """Get a node by its UUID from either pending or committed nodes."""
        return (
            self.pending_nodes.get(uuid) or 
            self.committed_nodes.get(uuid)
        )
        
    def get_edge(self, uuid: str) -> Optional[Edge]:
        """Get an edge by its UUID from either pending or committed edges."""
        return (
            self.pending_edges.get(uuid) or 
            self.committed_edges.get(uuid)
        )
        
    def commit_node(self, uuid: str) -> None:
        """Move a node from pending to committed state.
        
        Args:
            uuid: UUID of the node to commit
            
        Raises:
            ValueError: If node not found in pending state
        """
        node = self.pending_nodes.pop(uuid, None)
        if not node:
            raise ValueError(f"Node {uuid} not found in pending state")
            
        node.state = "committed"
        self.committed_nodes[uuid] = node
        logger.debug(f"Committed node: {node.name} ({node.uuid})")
        
    def commit_edge(self, uuid: str) -> None:
        """Move an edge from pending to committed state.
        
        Args:
            uuid: UUID of the edge to commit
            
        Raises:
            ValueError: If edge not found in pending state
        """
        edge = self.pending_edges.pop(uuid, None)
        if not edge:
            raise ValueError(f"Edge {uuid} not found in pending state")
            
        edge.state = "committed"
        self.committed_edges[uuid] = edge
        logger.debug(
            f"Committed edge: {edge.relation_type} from {edge.source_uuid} to {edge.target_uuid}"
        )
        
    def fail_node(self, uuid: str, error: str) -> None:
        """Move a node from pending to failed state.
        
        Args:
            uuid: UUID of the node to fail
            error: Error message explaining the failure
        """
        node = self.pending_nodes.pop(uuid, None)
        if node:
            node.state = "failed"
            self.failed_nodes[uuid] = node
            logger.error(f"Node {node.name} ({node.uuid}) failed: {error}")
            
    def fail_edge(self, uuid: str, error: str) -> None:
        """Move an edge from pending to failed state.
        
        Args:
            uuid: UUID of the edge to fail
            error: Error message explaining the failure
        """
        edge = self.pending_edges.pop(uuid, None)
        if edge:
            edge.state = "failed"
            self.failed_edges[uuid] = edge
            logger.error(
                f"Edge {edge.relation_type} from {edge.source_uuid} to {edge.target_uuid} "
                f"failed: {error}"
            )
            
    def commit_all(self) -> None:
        """Commit all pending nodes and edges."""
        # Commit nodes first
        for uuid in list(self.pending_nodes.keys()):
            self.commit_node(uuid)
            
        # Then commit edges
        for uuid in list(self.pending_edges.keys()):
            self.commit_edge(uuid)
            
    def rollback(self) -> None:
        """Move all pending items to failed state."""
        # Fail edges first
        for uuid in list(self.pending_edges.keys()):
            self.fail_edge(uuid, "Operation rolled back")
            
        # Then fail nodes
        for uuid in list(self.pending_nodes.keys()):
            self.fail_node(uuid, "Operation rolled back")
            
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the current context state."""
        return {
            "nodes": {
                "pending": len(self.pending_nodes),
                "committed": len(self.committed_nodes),
                "failed": len(self.failed_nodes)
            },
            "edges": {
                "pending": len(self.pending_edges),
                "committed": len(self.committed_edges),
                "failed": len(self.failed_edges)
            }
        }