"""
Resilion Knowledge Graph — NetworkX store with serialize/load.

GraphStore wraps a NetworkX DiGraph (directed graph) and provides:
  - Typed node insertion with Pydantic validation
  - Typed edge insertion
  - JSON serialization/deserialization (node-link format)
  - Basic query helpers (get_node, get_neighbors, get_edges_by_type)

Explicit NOT-TO-DO:
  - Do NOT introduce any graph database server (Neo4j, TigerGraph, etc.)
  - Do NOT use Cypher or any graph query language
  - All traversal is pure Python — see graph/traversal.py (Phase 2)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import networkx as nx

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from graph.schema import BaseNode, EdgeAttrs, EdgeType, NodeType


class GraphStore:
    """
    NetworkX DiGraph wrapper for the Resilion knowledge graph.

    Usage:
        gs = GraphStore()
        gs.add_node(event_node)
        gs.add_node(source_node)
        gs.add_edge(event_node.node_id, source_node.node_id, EdgeType.REPORTED_BY)
        gs.save("graph_state.json")

        gs2 = GraphStore.load("graph_state.json")
    """

    def __init__(self, name: str = "resilion-knowledge-graph") -> None:
        self.graph: nx.DiGraph = nx.DiGraph(name=name)
        self._created_at: str = datetime.utcnow().isoformat() + "Z"

    # ── Node operations ────────────────────────────────────────────────────────

    def add_node(self, node: BaseNode) -> None:
        """
        Insert a validated Pydantic node into the graph.
        If a node with the same node_id already exists, its attributes are updated.

        Args:
            node: Any Pydantic model inheriting from BaseNode (EventNode, SourceNode, etc.)
        """
        attrs = node.to_graph_attrs()
        if self.graph.has_node(node.node_id):
            # Update existing — merge new fields, don't overwrite created_at
            existing = self.graph.nodes[node.node_id]
            attrs["created_at"] = existing.get("created_at", attrs["created_at"])
            attrs["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.graph.add_node(node.node_id, **attrs)

    def add_node_raw(self, node_id: str, **attrs: Any) -> None:
        """
        Insert a node from a raw attribute dict (used during deserialization).
        Prefer add_node() for normal use — this bypasses Pydantic validation.
        """
        self.graph.add_node(node_id, **attrs)

    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        """Return node attribute dict, or None if not found."""
        if self.graph.has_node(node_id):
            return dict(self.graph.nodes[node_id])
        return None

    def get_nodes_by_type(self, node_type: NodeType) -> list[dict[str, Any]]:
        """Return all nodes of a given NodeType."""
        return [
            {"node_id": nid, **attrs}
            for nid, attrs in self.graph.nodes(data=True)
            if attrs.get("node_type") == node_type.value
        ]

    # ── Edge operations ────────────────────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        confidence: float = 1.0,
        **extra_attrs: Any,
    ) -> None:
        """
        Insert a typed, directed edge between two nodes.

        Args:
            source_id:  Source node ID (must exist in graph)
            target_id:  Target node ID (must exist in graph)
            edge_type:  EdgeType enum value
            confidence: Edge confidence score (0.0 – 1.0)
            **extra_attrs: Any additional attributes to store on the edge
        """
        if not self.graph.has_node(source_id):
            raise ValueError(f"Source node '{source_id}' not in graph. Add it first.")
        if not self.graph.has_node(target_id):
            raise ValueError(f"Target node '{target_id}' not in graph. Add it first.")

        attrs = EdgeAttrs(
            edge_type=edge_type,
            confidence=confidence,
        ).to_graph_attrs()
        attrs.update(extra_attrs)
        self.graph.add_edge(source_id, target_id, **attrs)

    def get_edges_by_type(self, edge_type: EdgeType) -> list[tuple[str, str, dict]]:
        """Return all edges of a given EdgeType as (source_id, target_id, attrs) tuples."""
        return [
            (u, v, data)
            for u, v, data in self.graph.edges(data=True)
            if data.get("edge_type") == edge_type.value
        ]

    def get_neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> list[str]:
        """
        Return IDs of nodes reachable from node_id via outgoing edges.
        Optionally filter by edge_type.
        """
        if not self.graph.has_node(node_id):
            return []
        neighbors = []
        for _, target, data in self.graph.out_edges(node_id, data=True):
            if edge_type is None or data.get("edge_type") == edge_type.value:
                neighbors.append(target)
        return neighbors

    def get_predecessors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> list[str]:
        """Return IDs of nodes that have an edge pointing TO node_id."""
        if not self.graph.has_node(node_id):
            return []
        predecessors = []
        for source, _, data in self.graph.in_edges(node_id, data=True):
            if edge_type is None or data.get("edge_type") == edge_type.value:
                predecessors.append(source)
        return predecessors

    # ── Stats ──────────────────────────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of graph stats (nodes, edges, type breakdown)."""
        type_counts: dict[str, int] = {}
        for _, attrs in self.graph.nodes(data=True):
            nt = attrs.get("node_type", "UNKNOWN")
            type_counts[nt] = type_counts.get(nt, 0) + 1

        edge_type_counts: dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            et = data.get("edge_type", "UNKNOWN")
            edge_type_counts[et] = edge_type_counts.get(et, 0) + 1

        return {
            "name": self.graph.graph.get("name", "resilion-knowledge-graph"),
            "created_at": self._created_at,
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "nodes_by_type": type_counts,
            "edges_by_type": edge_type_counts,
        }

    # ── Serialization ──────────────────────────────────────────────────────────

    def save(self, path: str | Path) -> Path:
        """
        Serialize the graph to JSON using NetworkX node-link format.
        All node and edge attributes are preserved.

        Args:
            path: File path to write to (will be created/overwritten)

        Returns:
            Path to the written file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = nx.node_link_data(self.graph)
        # Add our metadata
        data["_resilion_meta"] = {
            "created_at": self._created_at,
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "format_version": "1.0",
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return path

    @classmethod
    def load(cls, path: str | Path) -> "GraphStore":
        """
        Deserialize a graph from a JSON file written by save().

        Args:
            path: File path to read from

        Returns:
            A new GraphStore instance with the loaded graph

        Raises:
            FileNotFoundError: if path doesn't exist
            ValueError: if JSON is invalid or missing expected structure
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Graph state file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.pop("_resilion_meta", {})
        gs = cls()
        gs.graph = nx.node_link_graph(data)
        gs._created_at = meta.get("created_at", gs._created_at)
        return gs

    def __repr__(self) -> str:
        return (
            f"GraphStore(nodes={self.node_count}, edges={self.edge_count}, "
            f"created={self._created_at})"
        )
