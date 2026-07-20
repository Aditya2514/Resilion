"""
Resilion Knowledge Graph — Reference data seeding.

Seeds the graph with the fixed vocabulary of Corridors, Refineries,
Industries, and Alternative Suppliers that every later phase depends on.

This reference structure exists BEFORE any event ever comes in.
The LLM extraction agent (Phase 1) must ONLY tag entities from this seeded
vocabulary — it must never generate free-text entity names.

Graph structure after seeding:
  Corridors → (SUPPLIES) → Refineries → (SERVES) → Industries
  Corridors → (SUPPLIES) → Suppliers (for Orchestrator use in Phase 3)

Exit criteria for seeding:
  - All 3 corridors present
  - All 3 refineries present
  - 3 alternative suppliers present
  - All 4 industries present
  - Correct SUPPLIES and SERVES edges wired
"""

from __future__ import annotations

import sys

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from graph.schema import (
    CorridorNode, RefineryNode, IndustryNode, SupplierNode, EdgeType, NodeType
)
from graph.store import GraphStore


def seed_graph() -> GraphStore:
    """
    Create a fresh GraphStore and seed it with the reference vocabulary.

    Returns:
        A seeded GraphStore ready to receive Event nodes.
    """
    gs = GraphStore(name="resilion-knowledge-graph")

    # ── 1. Corridors ────────────────────────────────────────────────────────────
    hormuz = CorridorNode(
        node_id="corridor:strait_of_hormuz",
        name="Strait of Hormuz",
        region="Persian Gulf / Gulf of Oman",
        chokepoint=True,
        daily_throughput_mbpd=21.0,   # ~21 million bbl/day in normal conditions
        risk_level="CRITICAL",         # Ongoing blockade as of July 2026
        notes=(
            "Single most critical chokepoint for India crude imports (~40-45% of supply). "
            "2026 crisis: virtual shutdown Feb 2026, US blockade reinstated Jul 14 2026, "
            "20% cargo fee imposed. Brent spiked 9.5% above $83 on blockade news."
        ),
    )

    bab_mandeb = CorridorNode(
        node_id="corridor:bab_el_mandeb",
        name="Bab-el-Mandeb / Red Sea corridor",
        region="Red Sea / Gulf of Aden",
        chokepoint=True,
        daily_throughput_mbpd=6.2,    # ~6.2 million bbl/day
        risk_level="HIGH",
        notes=(
            "Connects Red Sea to Gulf of Aden. Houthi attacks on shipping 2023-2025 "
            "forced major rerouting via Cape of Good Hope. Still elevated risk."
        ),
    )

    malacca = CorridorNode(
        node_id="corridor:strait_of_malacca",
        name="Strait of Malacca",
        region="Southeast Asia",
        chokepoint=True,
        daily_throughput_mbpd=16.0,
        risk_level="ELEVATED",
        notes="Key route for Middle East crude to China, Japan, South Korea, India east coast.",
    )

    for corridor_node in [hormuz, bab_mandeb, malacca]:
        gs.add_node(corridor_node)

    # ── 2. Refineries ───────────────────────────────────────────────────────────
    jamnagar = RefineryNode(
        node_id="refinery:jamnagar_reliance",
        name="Jamnagar Refinery (Reliance)",
        operator="Reliance Industries",
        country="India",
        capacity_mbpd=1.24,    # world's largest single-location refinery
        corridor_dependence=["Strait of Hormuz", "Bab-el-Mandeb / Red Sea corridor"],
        notes="World's largest refinery complex. Primary crude from Middle East via Hormuz.",
    )

    panipat = RefineryNode(
        node_id="refinery:panipat_ioc",
        name="Panipat Refinery (IOC)",
        operator="Indian Oil Corporation",
        country="India",
        capacity_mbpd=0.30,
        corridor_dependence=["Strait of Hormuz"],
        notes="IOC's largest refinery. Processes Middle East sour crude.",
    )

    mumbai = RefineryNode(
        node_id="refinery:mumbai_bpcl",
        name="Mumbai Refinery (BPCL)",
        operator="Bharat Petroleum Corporation",
        country="India",
        capacity_mbpd=0.24,
        corridor_dependence=["Strait of Hormuz", "Bab-el-Mandeb / Red Sea corridor"],
        notes="Coastal refinery serving Mumbai region. Imports via Arabian Sea.",
    )

    for refinery_node in [jamnagar, panipat, mumbai]:
        gs.add_node(refinery_node)

    # ── 3. Alternative Suppliers ────────────────────────────────────────────────
    # These are the Orchestrator's (Phase 3) alternative sourcing options
    # when Hormuz/Bab-el-Mandeb routes are disrupted.

    russia = SupplierNode(
        node_id="supplier:russian_urals",
        name="Russian Urals Crude (via alternative routing)",
        country="Russia",
        crude_grade="Urals",
        typical_route="Arctic / Baltic / Black Sea → Cape of Good Hope → Indian Ocean",
        api_gravity=31.7,
        sulfur_content=1.3,
        notes=(
            "Available at discounted prices post-2022 sanctions. Requires longer tanker routes "
            "if Bab-el-Mandeb closed. India significantly increased Russian crude imports 2022-2024."
        ),
    )

    west_africa = SupplierNode(
        node_id="supplier:west_african_crude",
        name="West African Crude (Nigeria/Angola)",
        country="Nigeria / Angola",
        crude_grade="Bonny Light / Cabinda",
        typical_route="Gulf of Guinea → Cape of Good Hope → Indian Ocean",
        api_gravity=35.0,
        sulfur_content=0.2,
        notes=(
            "Light sweet crude, minimal Hormuz exposure. "
            "Longer voyage than Middle East but Strait-independent. "
            "Suitable for Jamnagar and Mumbai refineries."
        ),
    )

    us_wti = SupplierNode(
        node_id="supplier:us_wti_export",
        name="US WTI Export (via Cape of Good Hope routing)",
        country="United States",
        crude_grade="WTI Midland",
        typical_route="US Gulf Coast → Cape of Good Hope → Indian Ocean",
        api_gravity=40.8,
        sulfur_content=0.24,
        notes=(
            "Light sweet crude from US shale. Zero Hormuz/Bab-el-Mandeb exposure. "
            "Longer voyage (~30 days extra vs Middle East) but geopolitically diversified. "
            "India-US strategic partnership makes this a viable option."
        ),
    )

    for supplier_node in [russia, west_africa, us_wti]:
        gs.add_node(supplier_node)

    # ── 4. Industries ───────────────────────────────────────────────────────────
    power_gen = IndustryNode(
        node_id="industry:power_generation",
        name="Power generation",
        crude_dependence="HIGH",
        notes="Fuel oil and naphtha from refinery for power plants and grid backup.",
    )

    petrochem = IndustryNode(
        node_id="industry:petrochemicals",
        name="Petrochemicals",
        crude_dependence="HIGH",
        notes="Feedstock for plastics, fertilizers, synthetic fiber — Jamnagar is primary supplier.",
    )

    transport = IndustryNode(
        node_id="industry:transportation_aviation",
        name="Transportation fuel / aviation",
        crude_dependence="HIGH",
        notes="Petrol, diesel, ATF (aviation turbine fuel) — direct crude-to-pump supply chain.",
    )

    lpg = IndustryNode(
        node_id="industry:domestic_lpg",
        name="Domestic LPG distribution",
        crude_dependence="MEDIUM",
        notes="LPG for domestic cooking. ~88% of Indian households use LPG. Politically sensitive.",
    )

    for industry_node in [power_gen, petrochem, transport, lpg]:
        gs.add_node(industry_node)

    # ── 5. Wire SUPPLIES edges: Corridor → Refinery ─────────────────────────────
    # Jamnagar: depends on Hormuz (primary) and Bab-el-Mandeb (secondary)
    gs.add_edge("corridor:strait_of_hormuz", "refinery:jamnagar_reliance",
                EdgeType.SUPPLIES, confidence=1.0,
                notes="~40-45% of India crude supply transits Hormuz; primary route to Jamnagar")
    gs.add_edge("corridor:bab_el_mandeb", "refinery:jamnagar_reliance",
                EdgeType.SUPPLIES, confidence=0.8,
                notes="Secondary route via Red Sea / Suez Canal for West African and Russian crude")

    # Panipat: primarily Hormuz
    gs.add_edge("corridor:strait_of_hormuz", "refinery:panipat_ioc",
                EdgeType.SUPPLIES, confidence=1.0,
                notes="IOC predominantly imports Middle East sour crude via Hormuz")

    # Mumbai: Hormuz and Bab-el-Mandeb
    gs.add_edge("corridor:strait_of_hormuz", "refinery:mumbai_bpcl",
                EdgeType.SUPPLIES, confidence=1.0,
                notes="Primary Middle East crude supply route")
    gs.add_edge("corridor:bab_el_mandeb", "refinery:mumbai_bpcl",
                EdgeType.SUPPLIES, confidence=0.7,
                notes="Secondary route for diversified crude imports")

    # Alternative supplier reachability (via non-Hormuz routes)
    gs.add_edge("supplier:russian_urals", "refinery:jamnagar_reliance",
                EdgeType.SUPPLIES, confidence=0.7,
                notes="Russian Urals via Cape of Good Hope or Arctic route — Hormuz-independent")
    gs.add_edge("supplier:west_african_crude", "refinery:jamnagar_reliance",
                EdgeType.SUPPLIES, confidence=0.8,
                notes="West African light crude — Cape of Good Hope route — Hormuz-independent")
    gs.add_edge("supplier:west_african_crude", "refinery:mumbai_bpcl",
                EdgeType.SUPPLIES, confidence=0.7,
                notes="Light sweet crude compatible with Mumbai refinery configuration")
    gs.add_edge("supplier:us_wti_export", "refinery:jamnagar_reliance",
                EdgeType.SUPPLIES, confidence=0.6,
                notes="WTI via Cape of Good Hope — longest route but zero chokepoint exposure")

    # ── 6. Wire SERVES edges: Refinery → Industry ───────────────────────────────
    # Jamnagar serves all four industries (largest Indian refinery)
    for industry_id in [
        "industry:power_generation",
        "industry:petrochemicals",
        "industry:transportation_aviation",
        "industry:domestic_lpg",
    ]:
        gs.add_edge("refinery:jamnagar_reliance", industry_id,
                    EdgeType.SERVES, confidence=1.0)

    # Panipat: transport fuels, petrochem, LPG
    for industry_id in [
        "industry:transportation_aviation",
        "industry:petrochemicals",
        "industry:domestic_lpg",
    ]:
        gs.add_edge("refinery:panipat_ioc", industry_id,
                    EdgeType.SERVES, confidence=1.0)

    # Mumbai: transport fuels, power, LPG (western India focus)
    for industry_id in [
        "industry:transportation_aviation",
        "industry:power_generation",
        "industry:domestic_lpg",
    ]:
        gs.add_edge("refinery:mumbai_bpcl", industry_id,
                    EdgeType.SERVES, confidence=1.0)

    return gs


if __name__ == "__main__":
    gs = seed_graph()
    summary = gs.summary()

    print("=" * 60)
    print("Graph Seed — Phase 0 Reference Structure")
    print("=" * 60)
    print(f"\n  Total nodes: {summary['total_nodes']}")
    print(f"  Total edges: {summary['total_edges']}")
    print(f"\n  Nodes by type:")
    for nt, count in sorted(summary["nodes_by_type"].items()):
        print(f"    {nt:12s}: {count}")
    print(f"\n  Edges by type:")
    for et, count in sorted(summary["edges_by_type"].items()):
        print(f"    {et:20s}: {count}")

    print(f"\n  Corridor → Refinery (SUPPLIES) paths:")
    from graph.schema import EdgeType as ET2
    for src, tgt, data in gs.get_edges_by_type(ET2.SUPPLIES):
        src_name = gs.get_node(src).get("name", src)
        tgt_name = gs.get_node(tgt).get("name", tgt)
        print(f"    {src_name}  →  {tgt_name}  (confidence: {data['confidence']})")
