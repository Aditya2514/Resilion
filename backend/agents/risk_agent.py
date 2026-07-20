"""
Resilion — Risk Intelligence Agent (Watcher): Phase 1 Extraction Pipeline.

Converts raw article text into validated, graph-ready EventNode + SourceNode pairs.

Pipeline:
    1. Pre-filter with is_risk_relevant() — no LLM call if irrelevant (avoids wasted tokens)
    2. Structured LLM call (Gemini Flash) with Pydantic response schema
    3. Post-extraction normalization: corridor/severity/event_type forced to seeded vocabulary
    4. Confidence score calculation (formula documented in config.py)
    5. EventNode + SourceNode construction using graph/schema.py models
    6. Graph insertion via GraphStore (REPORTED_BY + OCCURRED_IN edges)

Design principles enforced here:
    - No fabricated fallbacks. If extraction fails, this function returns None and logs why.
    - Corridor is ALWAYS post-validated against CORRIDORS list. LLM output is never trusted raw.
    - Confidence = 0.3 base + corroboration boost (same corridor+event_type within 4h window)
      + recency multiplier (decays 1.0→0.5 over 72h).
    - Corroboration proxy caveat: this counts "same corridor+event_type within 4h" as a proxy
      for independent source confirmation. Two DIFFERENT disruptions in the same corridor+type
      within 4h would still increment each other's score. Real corroboration (same underlying
      incident, not just same category) requires CO_OCCURS_WITH deduplication — that's Phase 2's
      job. This proxy is explicitly labeled as an approximation, not the final answer.

Usage:
    agent = RiskAgent()
    result = agent.extract_and_insert(
        raw_text="...",
        metadata={"url": "...", "publisher": "Guardian", "published_at": "2026-07-20T..."},
        graph_store=gs,
    )
    # Returns ExtractionResult(event_node, source_node, was_inserted, rejection_reason)
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Allow running this file directly for quick tests
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field, field_validator

from config import (
    CORRIDORS,
    GEMINI_API_KEY,
    GEMINI_EXTRACTION_MODEL,
    CONFIDENCE_BASE,
    CONFIDENCE_PER_CORROBORATING_SOURCE,
    CONFIDENCE_MAX_CORROBORATING,
    RECENCY_DECAY_HOURS,
    RECENCY_MAX_MULTIPLIER,
    RECENCY_MIN_MULTIPLIER,
)
from data_sources.rss import is_risk_relevant
from graph.schema import (
    EdgeType,
    EventNode,
    EventType,
    NodeType,
    SeverityLevel,
    SourceNode,
)
from graph.store import GraphStore


# ── Gemini client setup ────────────────────────────────────────────────────────

def _get_gemini_client() -> genai.Client:
    """
    Initialise and return a Gemini client using the new google.genai SDK.

    Fails loudly if GEMINI_API_KEY is not set. No silent fallback.
    Get a free key at: https://aistudio.google.com/
    """
    if not GEMINI_API_KEY:
        raise EnvironmentError(
            "\n" + "=" * 65 + "\n"
            "[RiskAgent] GEMINI_API_KEY is not configured.\n\n"
            "This is the application's runtime extraction key, separate\n"
            "from any coding-agent credits. To set it:\n\n"
            "  1. Go to https://aistudio.google.com/ and create a free API key.\n"
            "  2. Add to your .env file (project root):\n"
            "       GEMINI_API_KEY=your_key_here\n"
            "  3. Re-run this script.\n\n"
            "Do NOT hardcode the key here.\n"
            + "=" * 65
        )
    return genai.Client(api_key=GEMINI_API_KEY)


# ── LLM extraction schema (Pydantic) ──────────────────────────────────────────

# These string constants mirror EventType/SeverityLevel enums.
# They are passed as explicit choices to the LLM so it can only pick from our vocabulary.
_CORRIDOR_OPTIONS = CORRIDORS + ["null"]  # LLM sees "null" as a valid choice
_EVENT_TYPE_OPTIONS = [e.value for e in EventType]
_SEVERITY_OPTIONS = [s.value for s in SeverityLevel]


class ExtractedEvent(BaseModel):
    """
    Schema for LLM-extracted event data. Used both as the prompt response schema
    and as the validated intermediate before building EventNode/SourceNode.

    All string fields are constrained to our seeded vocabulary.
    The LLM never generates free-text entity names for corridor/event_type/severity.
    """
    event_type: str = Field(
        ...,
        description=(
            f"Type of geopolitical/supply-chain event. "
            f"MUST be one of: {_EVENT_TYPE_OPTIONS}"
        ),
    )
    corridor: Optional[str] = Field(
        None,
        description=(
            f"Maritime shipping corridor affected. "
            f"MUST be exactly one of: {CORRIDORS}. "
            f"Set to null if the event is not corridor-specific or location is unclear."
        ),
    )
    severity: str = Field(
        ...,
        description=(
            f"Severity of supply chain impact. "
            f"MUST be one of: {_SEVERITY_OPTIONS}. "
            f"LOW=routine/minor, MODERATE=partial disruption, "
            f"HIGH=significant multi-refinery impact, CRITICAL=near-shutdown."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "1-3 sentence factual description of what happened and its supply chain significance. "
            "Do not speculate. Do not include information not in the source text."
        ),
    )
    is_supply_chain_relevant: bool = Field(
        ...,
        description=(
            "Set to true ONLY if this article describes a real geopolitical, military, policy, "
            "or shipping incident that directly impacts or threatens crude oil/energy supply chains "
            "(e.g., blockades, sanctions, drone attacks on tankers, refinery damage, price spikes). "
            "Set to false for general domestic politics, sports, entertainment, or unrelated news."
        ),
    )
    occurred_at_hint: Optional[str] = Field(
        None,
        description="Best estimate of when the event occurred (ISO 8601 date/datetime if inferable from text, else null).",
    )
    region: Optional[str] = Field(
        None,
        description="Country or sub-region where the event occurred (e.g. 'Iran', 'Persian Gulf', 'Red Sea'). Free text is fine here.",
    )

    @field_validator("event_type")
    @classmethod
    def event_type_must_be_valid(cls, v: str) -> str:
        if v not in _EVENT_TYPE_OPTIONS:
            # Attempt case-insensitive match before failing
            upper = v.upper().replace(" ", "_")
            if upper in _EVENT_TYPE_OPTIONS:
                return upper
            raise ValueError(
                f"event_type '{v}' not in allowed vocabulary: {_EVENT_TYPE_OPTIONS}"
            )
        return v

    @field_validator("severity")
    @classmethod
    def severity_must_be_valid(cls, v: str) -> str:
        if v not in _SEVERITY_OPTIONS:
            upper = v.upper()
            if upper in _SEVERITY_OPTIONS:
                return upper
            raise ValueError(
                f"severity '{v}' not in allowed vocabulary: {_SEVERITY_OPTIONS}"
            )
        return v

    @field_validator("corridor")
    @classmethod
    def corridor_must_be_seeded_or_null(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "null" or v == "":
            return None
        if v in CORRIDORS:
            return v
        # Fuzzy match: LLM sometimes says "Strait of Hormuz" without perfect casing
        for seeded in CORRIDORS:
            if v.lower() in seeded.lower() or seeded.lower() in v.lower():
                return seeded
        # Not in our list — set to None rather than propagating an invented name
        return None


# ── Confidence scoring ─────────────────────────────────────────────────────────

def _compute_recency_multiplier(occurred_at_str: Optional[str]) -> float:
    """
    Recency multiplier decays from RECENCY_MAX_MULTIPLIER (1.0) to
    RECENCY_MIN_MULTIPLIER (0.5) linearly over RECENCY_DECAY_HOURS (72h).

    If occurred_at is None or unparseable, returns the midpoint 0.75.
    """
    if not occurred_at_str:
        return (RECENCY_MAX_MULTIPLIER + RECENCY_MIN_MULTIPLIER) / 2.0

    try:
        # Handle both naive and timezone-aware datetimes
        if occurred_at_str.endswith("Z"):
            occurred_at_str = occurred_at_str[:-1] + "+00:00"
        occurred_at = datetime.fromisoformat(occurred_at_str)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        age_hours = (now - occurred_at).total_seconds() / 3600.0
        if age_hours < 0:
            age_hours = 0.0
        decay_fraction = min(age_hours / RECENCY_DECAY_HOURS, 1.0)
        multiplier = RECENCY_MAX_MULTIPLIER - decay_fraction * (
            RECENCY_MAX_MULTIPLIER - RECENCY_MIN_MULTIPLIER
        )
        return round(multiplier, 3)
    except (ValueError, TypeError):
        return (RECENCY_MAX_MULTIPLIER + RECENCY_MIN_MULTIPLIER) / 2.0


def _count_corroborating_events(
    graph_store: GraphStore,
    corridor: Optional[str],
    event_type: str,
    occurred_at_str: Optional[str],
) -> int:
    """
    Count existing graph EVENT nodes that share the same corridor AND event_type
    within a ±4-hour window of occurred_at.

    IMPORTANT — Phase 1 corroboration proxy:
        This counts "same corridor + same event_type within ±4h" as a proxy for
        independent source confirmation of the same incident. This is an approximation:
        two genuinely different disruptions sharing corridor+type in a 4h window would
        still increment each other's score. True corroboration (same underlying incident,
        not same category) requires CO_OCCURS_WITH event deduplication — that is
        Phase 2's job. This function is a stated proxy, not a claim of correctness.

    Returns: int in range [0, CONFIDENCE_MAX_CORROBORATING]
    """
    if not corridor or not occurred_at_str:
        return 0

    try:
        if occurred_at_str.endswith("Z"):
            occurred_at_str = occurred_at_str[:-1] + "+00:00"
        target_dt = datetime.fromisoformat(occurred_at_str)
        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0

    window = timedelta(hours=4)
    count = 0

    event_nodes = graph_store.get_nodes_by_type(NodeType.EVENT)
    for node in event_nodes:
        if node.get("corridor") != corridor:
            continue
        if node.get("event_type") != event_type:
            continue
        existing_dt_str = node.get("occurred_at")
        if not existing_dt_str:
            continue
        try:
            if existing_dt_str.endswith("Z"):
                existing_dt_str = existing_dt_str[:-1] + "+00:00"
            existing_dt = datetime.fromisoformat(existing_dt_str)
            if existing_dt.tzinfo is None:
                existing_dt = existing_dt.replace(tzinfo=timezone.utc)
            if abs((existing_dt - target_dt).total_seconds()) <= window.total_seconds():
                count += 1
        except (ValueError, TypeError):
            continue

    return min(count, CONFIDENCE_MAX_CORROBORATING)


def compute_confidence(
    corroborating_sources: int,
    occurred_at_str: Optional[str],
) -> float:
    """
    Calculates confidence by scaling the base score (base + corroboration boost)
    by the recency multiplier:
        confidence = (0.3 + 0.2 × min(corroborating_sources, 3)) × recency_multiplier

    where:
        - base = 0.3
        - corroboration boost = 0.2 per source (up to 0.6 max)
        - recency_multiplier = decays from 1.0 (fresh) to 0.5 (72h+ old)

    This ensures that:
        - A fresh, uncorroborated event scores 0.300
        - A fresh, fully corroborated event (3+ sources) scores 0.900
        - An old, uncorroborated event scores 0.150
        - An old, fully corroborated event scores 0.450
    """
    recency = _compute_recency_multiplier(occurred_at_str)
    corroboration_boost = CONFIDENCE_PER_CORROBORATING_SOURCE * min(
        corroborating_sources, CONFIDENCE_MAX_CORROBORATING
    )
    base_confidence = CONFIDENCE_BASE + corroboration_boost
    raw = base_confidence * recency
    # Clamp to [0, 1]
    return round(min(max(raw, 0.0), 1.0), 3)


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class ExtractionResult:
    event_node: Optional[EventNode] = None
    source_node: Optional[SourceNode] = None
    was_inserted: bool = False
    was_risk_relevant: bool = False
    rejection_reason: Optional[str] = None
    raw_extracted: Optional[dict] = None  # raw LLM output dict for auditing


# ── Main agent class ───────────────────────────────────────────────────────────

class RiskAgent:
    """
    The Watcher: extracts structured risk events from article text and inserts
    them into the Resilion knowledge graph.

    Instantiate once per session (reuses the Gemini client across calls).
    """

    SYSTEM_PROMPT = """\
You are a risk intelligence analyst for an energy supply chain monitoring system.
Your job is to extract structured event data from raw news article text.

CRITICAL RULES:
1. Corridor MUST be one of exactly:
   - "Strait of Hormuz"
   - "Bab-el-Mandeb / Red Sea corridor"
   - "Strait of Malacca"
   - null (if the event is not corridor-specific)
   Do NOT invent corridor names. Do NOT use partial matches like just "Hormuz".

2. Event type MUST be one of exactly:
   MILITARY_ACTION, SANCTIONS, BLOCKADE, PIRACY, INFRASTRUCTURE,
   WEATHER, DIPLOMATIC, SHIPPING_ATTACK, DARK_VESSEL, PRICE_SPIKE, OTHER

3. Severity MUST be one of: LOW, MODERATE, HIGH, CRITICAL

4. Description must be factual — only what the article states. No speculation.

5. If the article does not describe a geopolitical or supply-chain risk event,
   return event_type=OTHER, severity=LOW, corridor=null, description="Non-risk article".
"""

    def __init__(self) -> None:
        self._client = _get_gemini_client()

    def extract_and_insert(
        self,
        raw_text: str,
        metadata: dict,
        graph_store: GraphStore,
        verbose: bool = False,
    ) -> ExtractionResult:
        """
        Full pipeline: pre-filter → LLM extract → normalize → score → insert.

        Args:
            raw_text:    Full or partial article text.
            metadata:    Dict with keys: url, publisher, published_at, title, source_tier.
            graph_store: Seeded GraphStore instance to insert into.
            verbose:     Print progress messages.

        Returns:
            ExtractionResult — always returned, never raises. Check .was_inserted.
        """
        title = metadata.get("title", "")
        url = metadata.get("url", "")
        publisher = metadata.get("publisher", "GUARDIAN")
        published_at = metadata.get("published_at", "")
        source_tier = int(metadata.get("source_tier", 3))

        # ── Step 1: Pre-filter ─────────────────────────────────────────────────
        if not is_risk_relevant(title, raw_text[:500]):
            if verbose:
                print(f"  [SKIP] Not risk-relevant: {title[:60]}")
            return ExtractionResult(
                was_risk_relevant=False,
                rejection_reason="Pre-filter: no risk signal keywords found in title/summary",
            )

        if verbose:
            print(f"  [EXTRACT] {title[:70]}")

        # ── Step 2: LLM structured extraction ─────────────────────────────────
        prompt = (
            f"Article title: {title}\n\n"
            f"Article text (may be truncated):\n{raw_text[:3000]}\n\n"
            "Extract the risk event from this article. "
            "If the article describes no supply chain risk event, classify it as OTHER/LOW."
        )

        try:
            response = self._client.models.generate_content(
                model=GEMINI_EXTRACTION_MODEL,
                contents=[self.SYSTEM_PROMPT, prompt],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedEvent,
                    temperature=0.0,   # deterministic extraction
                ),
            )
            raw_json = response.text
            extracted = ExtractedEvent.model_validate_json(raw_json)
        except Exception as e:
            if verbose:
                print(f"  [FAIL] LLM extraction error: {e}")
            return ExtractionResult(
                was_risk_relevant=True,
                rejection_reason=f"LLM extraction failed: {type(e).__name__}: {e}",
            )

        if verbose:
            print(f"    event_type={extracted.event_type}, corridor={extracted.corridor}, severity={extracted.severity}, relevant={extracted.is_supply_chain_relevant}")

        # ── Step 2.5: Relevance validation (Second line of defense) ───────────
        if not extracted.is_supply_chain_relevant:
            if verbose:
                print(f"    [REJECT] LLM classified as not supply chain relevant: {title[:60]}")
            return ExtractionResult(
                was_risk_relevant=False,
                rejection_reason="LLM classified as not supply chain relevant",
                raw_extracted=extracted.model_dump(),
            )

        # ── Step 3: Determine occurred_at ──────────────────────────────────────
        occurred_at = extracted.occurred_at_hint or published_at

        # ── Step 4: Confidence scoring ─────────────────────────────────────────
        corroborating = _count_corroborating_events(
            graph_store, extracted.corridor, extracted.event_type, occurred_at
        )
        confidence = compute_confidence(corroborating, occurred_at)

        # ── Step 5: Build node IDs ─────────────────────────────────────────────
        # Deterministic ID from URL so re-runs don't double-insert
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        event_node_id = f"event:guardian:{url_hash}"
        source_node_id = f"source:guardian:{url_hash}"
        domain = url.split("/")[2] if url.startswith("http") else "unknown"

        # ── Step 6: Build Pydantic models ──────────────────────────────────────
        source_node = SourceNode(
            node_id=source_node_id,
            name=publisher,
            tier=source_tier,
            url=url,
            published_at=published_at,
            domain=domain,
        )

        event_node = EventNode(
            node_id=event_node_id,
            event_type=EventType(extracted.event_type),
            title=title,
            description=extracted.description,
            occurred_at=occurred_at,
            corridor=extracted.corridor,  # already validated/normalized by Pydantic validator
            region=extracted.region,
            severity=SeverityLevel(extracted.severity),
            confidence=confidence,
            source_tier=source_tier,
            corroborating_sources=corroborating,
            source_node_ids=[source_node_id],
            raw_text_snippet=(raw_text[:500] if raw_text else None),
            extraction_model=GEMINI_EXTRACTION_MODEL,
        )

        # ── Step 7: Insert into graph ──────────────────────────────────────────
        graph_store.add_node(source_node)
        graph_store.add_node(event_node)
        graph_store.add_edge(
            event_node_id, source_node_id,
            EdgeType.REPORTED_BY,
            confidence=confidence,
            source_tier=source_tier,
        )

        # Wire OCCURRED_IN only if corridor is non-null and corridor node exists in graph
        if extracted.corridor:
            # Always look up by name — slug derivation is lossy for corridors with
            # slashes and hyphens (e.g. "Bab-el-Mandeb / Red Sea corridor")
            corridor_node_id = None
            all_corridors = graph_store.get_nodes_by_type(NodeType.CORRIDOR)
            for cn in all_corridors:
                if cn.get("name") == extracted.corridor:
                    corridor_node_id = cn["node_id"]
                    break

            if corridor_node_id is not None:
                graph_store.add_edge(
                    event_node_id, corridor_node_id,
                    EdgeType.OCCURRED_IN,
                    confidence=confidence,
                )
                event_node.corridor_node_id = corridor_node_id
            else:
                if verbose:
                    print(f"    [WARN] Corridor '{extracted.corridor}' not found in graph — OCCURRED_IN edge skipped")

        if verbose:
            print(f"    [OK] Inserted: {event_node_id} | confidence={confidence:.3f} | corridor={extracted.corridor}")

        return ExtractionResult(
            event_node=event_node,
            source_node=source_node,
            was_inserted=True,
            was_risk_relevant=True,
            raw_extracted=extracted.model_dump(),
        )

