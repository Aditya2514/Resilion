"""
Resilion Knowledge Graph — Traversal helpers (Phase 0 placeholder).

This module is intentionally minimal in Phase 0. The traversal logic
(walk outward from an Event to find affected Refineries and Industries,
compute disruption probability scores, build explanation paths) is
Phase 2 work.

What's here in Phase 0:
  - Skeleton function signatures with docstrings
  - Basic path-finding using nx.shortest_path (used by exit criteria)
  - A stub find_affected_industries() so Phase 1 tests can call something real

Phase 2 will fill in:
  - Disruption score computation per corridor/supplier
  - Cost-exposure estimates
  - Full graph-traced explanation paths (for Phase 3 recommendation rationale)
"""

from __future__ import annotations

import sys
from typing import Any, Optional

import networkx as nx

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from graph.schema import EdgeType, NodeType
from graph.store import GraphStore


def find_affected_industries(
    gs: GraphStore,
    corridor_node_id: str,
) -> list[dict[str, Any]]:
    """
    [PHASE 2 — STUB]
    Given a corridor node_id, walk outward via SUPPLIES → SERVES edges
    to find all Industry nodes reachable from this corridor.

    Returns list of dicts: {node_id, name, path (corridor→refinery→industry)}

    Phase 2 will add disruption probability scores and cost-exposure estimates.
    """
    affected = []

    # Walk: Corridor → Refinery (SUPPLIES)
    refinery_ids = gs.get_neighbors(corridor_node_id, edge_type=EdgeType.SUPPLIES)

    for refinery_id in refinery_ids:
        refinery_node = gs.get_node(refinery_id)
        if refinery_node is None:
            continue

        # Skip if this is a Supplier node, not a Refinery
        if refinery_node.get("node_type") not in (NodeType.REFINERY.value, "Refinery"):
            continue

        # Walk: Refinery → Industry (SERVES)
        industry_ids = gs.get_neighbors(refinery_id, edge_type=EdgeType.SERVES)
        for industry_id in industry_ids:
            industry_node = gs.get_node(industry_id)
            if industry_node is None:
                continue
            affected.append({
                "corridor_id": corridor_node_id,
                "refinery_id": refinery_id,
                "refinery_name": refinery_node.get("name", refinery_id),
                "industry_id": industry_id,
                "industry_name": industry_node.get("name", industry_id),
                "path": [corridor_node_id, refinery_id, industry_id],
                "disruption_score": None,  # Phase 2 will compute this
            })

    return affected


def find_path(
    gs: GraphStore,
    source_id: str,
    target_id: str,
) -> Optional[list[str]]:
    """
    Find the shortest directed path between two nodes.
    Returns None if no path exists.
    Uses nx.shortest_path (unweighted).
    """
    try:
        return nx.shortest_path(gs.graph, source=source_id, target=target_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def get_all_events_for_corridor(
    gs: GraphStore,
    corridor_node_id: str,
) -> list[dict[str, Any]]:
    """
    [PHASE 2 — STUB]
    Return all Event nodes linked to a corridor via OCCURRED_IN edges.
    Phase 2 will sort these by severity and recency for scoring.
    """
    event_ids = gs.get_predecessors(corridor_node_id, edge_type=EdgeType.OCCURRED_IN)
    events = []
    for event_id in event_ids:
        node = gs.get_node(event_id)
        if node and node.get("node_type") == NodeType.EVENT.value:
            events.append({"node_id": event_id, **node})
    return events


def compute_disruption_score(
    gs: GraphStore,
    corridor_node_id: str,
) -> float:
    """
    [PHASE 2 — STUB]
    Compute a disruption probability score (0.0–1.0) for a corridor
    based on active Event nodes and their confidence/severity.
    Returns 0.0 until Phase 2 implements the scoring logic.
    """
    # TODO (Phase 2): aggregate event severity × confidence for all events
    # linked to this corridor via OCCURRED_IN edges
    return 0.0


def explain_recommendation(
    gs: GraphStore,
    recommendation_node_id: str,
) -> list[dict[str, Any]]:
    """
    [PHASE 3 — STUB]
    Walk backward from a recommendation node through the graph to produce
    a human-readable, graph-traced explanation chain:
      Recommendation ← Disruption Score ← Event ← Source

    Returns an ordered list of {node_id, node_type, name, edge_type} steps.
    This is the structural explainability core of the system — never free-text LLM.
    """
    # TODO (Phase 3): implement full backward path walk
    return []
