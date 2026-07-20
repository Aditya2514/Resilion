"""
Resilion Knowledge Graph — Node and Edge Schema.

Defines all node types, edge types, and Pydantic validation models for the
NetworkX graph. Every node inserted into the graph must match one of these
Pydantic models to ensure schema consistency before Phase 1 ingestion begins.

Node types:
  EVENT      — A real-world event (disruption, sanction, attack, blockade)
  SOURCE     — A data source that reported an event
  CORRIDOR   — A maritime shipping corridor (Hormuz, Bab-el-Mandeb, Malacca)
  REFINERY   — A refinery or crude processing facility
  INDUSTRY   — A downstream industry sector served by crude supply
  SANCTION   — An OFAC or international sanctions designation

Edge types:
  REPORTED_BY      — Event → Source (this event was reported by this source)
  OCCURRED_IN      — Event → Corridor (this event occurred in this corridor)
  CO_OCCURS_WITH   — Event ↔ Event (two events co-occur in time/space)
  SUPPLIES         — Corridor → Refinery (corridor supplies this refinery)
  SERVES           — Refinery → Industry (refinery serves this industry sector)
  TARGETS          — Sanction → Corridor|Refinery|Supplier (sanction targets entity)

Design principle: explainability is structural.
A recommendation's "why" is a path walk through real graph edges, not a
free-text LLM justification. Preserve edge metadata (confidence, source_tier,
timestamp) — they are the audit trail.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Node Types ─────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    EVENT     = "Event"
    SOURCE    = "Source"
    CORRIDOR  = "Corridor"
    REFINERY  = "Refinery"
    INDUSTRY  = "Industry"
    SANCTION  = "Sanction"
    VESSEL    = "Vessel"          # for synthetic AIS / tanker nodes (Phase 2+)
    SUPPLIER  = "Supplier"        # alternative crude suppliers


# ── Edge Types ─────────────────────────────────────────────────────────────────

class EdgeType(str, Enum):
    REPORTED_BY    = "REPORTED_BY"
    OCCURRED_IN    = "OCCURRED_IN"
    CO_OCCURS_WITH = "CO_OCCURS_WITH"
    SUPPLIES       = "SUPPLIES"
    SERVES         = "SERVES"
    TARGETS        = "TARGETS"
    TRANSITS       = "TRANSITS"   # Vessel → Corridor (Phase 2+)
    DIVERTS_TO     = "DIVERTS_TO" # Event / Vessel → alternative route (Phase 3+)


# ── Severity Scale ─────────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    LOW      = "LOW"       # Routine disruption, minimal supply impact
    MODERATE = "MODERATE"  # Partial disruption, some rerouting needed
    HIGH     = "HIGH"      # Significant disruption, multi-refinery impact
    CRITICAL = "CRITICAL"  # Near-shutdown, strategic reserve consideration


# ── Event Types ────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    MILITARY_ACTION   = "MILITARY_ACTION"    # Missile attack, naval incident
    SANCTIONS         = "SANCTIONS"          # New OFAC/UN designation
    BLOCKADE          = "BLOCKADE"           # Strait/port blockade
    PIRACY            = "PIRACY"             # Piracy or vessel seizure
    INFRASTRUCTURE    = "INFRASTRUCTURE"     # Refinery / pipeline damage
    WEATHER           = "WEATHER"            # Storm, fog, seasonal closure
    DIPLOMATIC        = "DIPLOMATIC"         # Treaty, negotiation, diplomacy
    SHIPPING_ATTACK   = "SHIPPING_ATTACK"    # Drone / missile vs vessel
    DARK_VESSEL       = "DARK_VESSEL"        # AIS transponder deactivation
    PRICE_SPIKE       = "PRICE_SPIKE"        # Significant crude price move
    OTHER             = "OTHER"


# ── Pydantic Node Models ───────────────────────────────────────────────────────

class BaseNode(BaseModel):
    """Base fields required on every node."""
    node_id: str = Field(..., description="Unique node identifier within the graph")
    node_type: NodeType
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    # Optional free-text notes (never used for explainability — graph edges do that)
    notes: Optional[str] = None

    def to_graph_attrs(self) -> dict[str, Any]:
        """Return a flat dict suitable for nx.DiGraph node attributes."""
        return self.model_dump()


class EventNode(BaseNode):
    """
    Represents a real-world event that may affect crude oil supply chains.
    Phase 1 (LLM extraction) creates these nodes from news/data source text.
    """
    node_type: NodeType = NodeType.EVENT
    event_type: EventType
    title: str = Field(..., description="Short human-readable title of the event")
    description: str = Field(..., description="1-3 sentence factual description")
    occurred_at: Optional[str] = None          # ISO8601 or YYYYMMDD
    corridor: Optional[str] = None             # Must be from CORRIDORS list in config.py
    region: Optional[str] = None               # Country or sub-region
    severity: SeverityLevel = SeverityLevel.MODERATE
    # Confidence scoring (see config.py for formula)
    confidence: float = Field(0.3, ge=0.0, le=1.0)
    source_tier: int = Field(2, ge=1, le=3,
        description="1=official, 2=structured event db, 3=news/rss")
    corroborating_sources: int = Field(0, ge=0)
    # Graph linkage IDs (set after insertion)
    source_node_ids: list[str] = Field(default_factory=list)
    corridor_node_id: Optional[str] = None
    # Raw text that produced this event (for audit trail)
    raw_text_snippet: Optional[str] = None      # max 500 chars
    extraction_model: Optional[str] = None      # Phase 1: which model extracted this

    @field_validator("corridor")
    @classmethod
    def corridor_must_be_seeded(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Import here to avoid circular at module load
        from config import CORRIDORS
        if v not in CORRIDORS:
            raise ValueError(
                f"corridor '{v}' not in seeded CORRIDORS list. "
                f"Valid values: {CORRIDORS}. "
                f"Phase 1 must constrain LLM to this vocabulary."
            )
        return v


class SourceNode(BaseNode):
    """
    Represents a data source that reported an event.
    Wired to EventNodes via REPORTED_BY edges.
    """
    node_type: NodeType = NodeType.SOURCE
    name: str = Field(..., description="Human-readable source name (e.g. 'GDELT', 'EIA')")
    tier: int = Field(..., ge=1, le=3, description="Source tier: 1=official, 2=structured, 3=news")
    url: Optional[str] = None
    published_at: Optional[str] = None
    domain: Optional[str] = None
    feed_name: Optional[str] = None


class CorridorNode(BaseNode):
    """
    A maritime shipping corridor that crude oil transits.
    Seeded at graph initialization — never created from news extraction.
    """
    node_type: NodeType = NodeType.CORRIDOR
    name: str
    region: str
    chokepoint: bool = True
    daily_throughput_mbpd: Optional[float] = None  # million barrels per day
    risk_level: str = "NORMAL"   # NORMAL | ELEVATED | CRITICAL
    notes: Optional[str] = None


class RefineryNode(BaseNode):
    """
    A refinery or crude processing facility.
    Seeded at graph initialization.
    """
    node_type: NodeType = NodeType.REFINERY
    name: str
    operator: Optional[str] = None
    country: str = "India"
    capacity_mbpd: Optional[float] = None    # million barrels per day
    corridor_dependence: list[str] = Field(default_factory=list)  # which corridors it depends on
    notes: Optional[str] = None


class IndustryNode(BaseNode):
    """
    A downstream industry sector served by crude supply from refineries.
    Seeded at graph initialization.
    """
    node_type: NodeType = NodeType.INDUSTRY
    name: str
    crude_dependence: str = "HIGH"   # HIGH | MEDIUM | LOW
    notes: Optional[str] = None


class SupplierNode(BaseNode):
    """
    An alternative crude oil supplier / sourcing option.
    Used by the Procurement Orchestrator (Phase 3) to rank alternatives.
    """
    node_type: NodeType = NodeType.SUPPLIER
    name: str
    country: str
    crude_grade: Optional[str] = None        # e.g. "Urals", "Bonny Light", "WTI"
    typical_route: Optional[str] = None      # corridor(s) used
    api_gravity: Optional[float] = None      # crude quality
    sulfur_content: Optional[float] = None   # % sulfur
    notes: Optional[str] = None


class SanctionNode(BaseNode):
    """
    An OFAC or international sanctions designation.
    Created from OFAC feed. TARGETS edges link to affected corridors/suppliers.
    """
    node_type: NodeType = NodeType.SANCTION
    name: str
    entity_type: str   # Individual, Entity, Vessel, Aircraft
    program: str       # OFAC program code
    ofac_uid: Optional[str] = None
    source_url: Optional[str] = None
    effective_date: Optional[str] = None
    notes: Optional[str] = None


# ── Edge Attribute Models ──────────────────────────────────────────────────────

class EdgeAttrs(BaseModel):
    """Base attributes attached to every edge in the graph."""
    edge_type: EdgeType
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None

    def to_graph_attrs(self) -> dict[str, Any]:
        return self.model_dump()
