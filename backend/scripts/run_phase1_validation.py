"""
Phase 1 Exit Criteria Validation Script.

Feeds 10 real Guardian articles from the historical archive through the
Risk Intelligence Agent (Watcher) extraction pipeline, then:
  1. Shows all extracted events with corridor, severity, confidence.
  2. Performs hand spot-checks on 3 articles (original text vs extracted fields).
  3. Verifies vocabulary containment — no invented corridor/event names.
  4. Prints updated graph node/edge counts.

Run from backend/ directory:
    python scripts/run_phase1_validation.py

Prerequisites:
    - GEMINI_API_KEY set in .env (get free key at https://aistudio.google.com/)
    - historical/events_2026_hormuz_crisis.json must exist (run build_archive.py first)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make sure we can import from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CORRIDORS, HISTORICAL_DIR
from graph.schema import EventType, NodeType, SeverityLevel
from graph.seed import seed_graph
from graph.store import GraphStore
from agents.risk_agent import RiskAgent

# ─────────────────────────────────────────────────────────────────────────────
ARCHIVE_PATH = HISTORICAL_DIR / "events_2026_hormuz_crisis.json"
NUM_ARTICLES = 10   # Phase 1 exit criteria: process 10 of 20 real articles
SPOT_CHECK_INDICES = [0, 1, 2]   # 0-indexed into the INSERTED list (not the raw list)

SEPARATOR = "=" * 70


def load_archive() -> list[dict]:
    if not ARCHIVE_PATH.exists():
        print(f"[ERROR] Archive not found: {ARCHIVE_PATH}")
        print("Run: python historical/build_archive.py")
        sys.exit(1)
    with open(ARCHIVE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    integrity = data.get("data_integrity", "UNKNOWN")
    if integrity != "REAL":
        print(f"[ERROR] Archive data_integrity is '{integrity}', expected 'REAL'.")
        print("This means the archive was built from fabricated fallback data.")
        print("Re-run: python historical/build_archive.py")
        sys.exit(1)
    records = data.get("records", [])
    print(f"[Archive] Loaded {len(records)} records | integrity={integrity}")
    return records


def run_validation() -> None:
    print(SEPARATOR)
    print("  RESILION — Phase 1 Exit Criteria: Risk Extraction Validation")
    print(SEPARATOR)

    # ── Step 1: Seed graph ────────────────────────────────────────────────────
    print("\n[Step 1] Seeding fresh reference graph...")
    gs = seed_graph()
    print(f"  Seeded: {gs.graph.number_of_nodes()} nodes, {gs.graph.number_of_edges()} edges")

    # ── Step 2: Load archive ──────────────────────────────────────────────────
    print("\n[Step 2] Loading real historical archive...")
    all_records = load_archive()

    # Take first NUM_ARTICLES regardless of risk-relevance filtering — the agent
    # will apply is_risk_relevant() internally and skip non-risk articles.
    candidate_records = all_records[:NUM_ARTICLES * 3]   # oversample to ensure 10 inserted

    # ── Step 3: Initialise agent ──────────────────────────────────────────────
    print("\n[Step 3] Initialising Risk Agent (Gemini Flash)...")
    try:
        agent = RiskAgent()
        print("  [OK] Agent ready.")
    except EnvironmentError as e:
        print(str(e))
        sys.exit(1)

    # ── Step 4: Extract + insert ──────────────────────────────────────────────
    print(f"\n[Step 4] Extracting from up to {len(candidate_records)} articles (target: {NUM_ARTICLES} insertions)...")
    print(SEPARATOR[:40])

    inserted_results = []
    skipped = []

    for i, record in enumerate(candidate_records):
        if len(inserted_results) >= NUM_ARTICLES:
            break

        title = record.get("title", "")
        raw_text = record.get("raw_text", "")
        url = record.get("url", "")
        published_at = record.get("date", "")
        source_tier = int(record.get("tier", 3))

        metadata = {
            "title": title,
            "url": url,
            "publisher": record.get("source", "GUARDIAN"),
            "published_at": published_at,
            "source_tier": source_tier,
        }

        result = agent.extract_and_insert(
            raw_text=raw_text,
            metadata=metadata,
            graph_store=gs,
            verbose=True,
        )

        if result.was_inserted:
            inserted_results.append((record, result))
        else:
            skipped.append((record, result))

    print(SEPARATOR[:40])
    print(f"\n  Inserted: {len(inserted_results)} events | Skipped (not risk-relevant): {len(skipped)}")

    if len(inserted_results) == 0:
        print("\n[ERROR] 0 events inserted — check that GEMINI_API_KEY is set and the archive has risk-relevant articles.")
        sys.exit(1)

    # ── Step 5: Display extraction table ──────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print("  EXTRACTED EVENTS SUMMARY")
    print(SEPARATOR)
    print(f"  {'#':<3} {'Title':<45} {'corridor':<25} {'severity':<10} {'conf':<7}")
    print("  " + "-" * 95)

    for idx, (record, result) in enumerate(inserted_results, 1):
        evt = result.event_node
        title_trunc = evt.title[:43] + ".." if len(evt.title) > 45 else evt.title
        corridor_trunc = (evt.corridor or "—")[:23]
        print(f"  {idx:<3} {title_trunc:<45} {corridor_trunc:<25} {evt.severity.value:<10} {evt.confidence:<7.3f}")

    # ── Step 6: Spot-check 3 articles ─────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print("  SPOT-CHECK: Original Text vs Extracted Fields (3 articles)")
    print(SEPARATOR)

    for sc_idx in SPOT_CHECK_INDICES:
        if sc_idx >= len(inserted_results):
            continue
        record, result = inserted_results[sc_idx]
        evt = result.event_node
        raw = result.raw_extracted or {}

        print(f"\n  Spot-check #{sc_idx + 1}: {evt.title[:70]}")
        print(f"  URL:      {record.get('url', '')}")
        print(f"  Published:{record.get('date', '')}")
        print()
        print(f"  -- Original text snippet (first 400 chars) --")
        snippet = (record.get("raw_text", "") or "")[:400]
        for line in snippet.split("\n")[:6]:
            print(f"     {line}")
        print()
        print(f"  -- Extracted fields --")
        print(f"     event_type:  {evt.event_type.value}")
        print(f"     corridor:    {evt.corridor or 'null'}")
        print(f"     severity:    {evt.severity.value}")
        print(f"     confidence:  {evt.confidence:.3f}")
        print(f"     description: {evt.description[:200]}")
        print()

    # ── Step 7: Vocabulary containment check ──────────────────────────────────
    print(SEPARATOR)
    print("  VOCABULARY CONTAINMENT CHECK")
    print(SEPARATOR)
    passed = True

    all_corridors_used = set()
    all_event_types_used = set()
    all_severities_used = set()

    for _, result in inserted_results:
        evt = result.event_node
        if evt.corridor:
            all_corridors_used.add(evt.corridor)
        all_event_types_used.add(evt.event_type.value)
        all_severities_used.add(evt.severity.value)

    valid_corridors = set(CORRIDORS)
    valid_event_types = {e.value for e in EventType}
    valid_severities = {s.value for s in SeverityLevel}

    # Check corridors
    invalid_corridors = all_corridors_used - valid_corridors
    if invalid_corridors:
        print(f"  [FAIL] Invented corridor names found: {invalid_corridors}")
        passed = False
    else:
        print(f"  [OK] All corridors in seeded vocabulary: {all_corridors_used or '{none assigned}'}")

    # Check event types
    invalid_types = all_event_types_used - valid_event_types
    if invalid_types:
        print(f"  [FAIL] Invalid event_type values found: {invalid_types}")
        passed = False
    else:
        print(f"  [OK] All event_types in vocabulary: {all_event_types_used}")

    # Check severities
    invalid_sev = all_severities_used - valid_severities
    if invalid_sev:
        print(f"  [FAIL] Invalid severity values found: {invalid_sev}")
        passed = False
    else:
        print(f"  [OK] All severities in vocabulary: {all_severities_used}")

    # ── Step 8: Graph counts ───────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print("  GRAPH COUNTS AFTER INSERTION")
    print(SEPARATOR)
    n_nodes = gs.graph.number_of_nodes()
    n_edges = gs.graph.number_of_edges()
    by_type = {}
    for _, attrs in gs.graph.nodes(data=True):
        t = attrs.get("node_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    print(f"  Total nodes: {n_nodes}")
    print(f"  Total edges: {n_edges}")
    print(f"  By type:")
    for t, count in sorted(by_type.items()):
        print(f"    {t:<20}: {count}")

    # ── Final result ───────────────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    all_good = passed and len(inserted_results) == NUM_ARTICLES

    if len(inserted_results) < NUM_ARTICLES:
        print(f"  [PARTIAL] Only {len(inserted_results)}/{NUM_ARTICLES} insertions.")
        print(f"  This may be because the archive lacks enough risk-relevant articles.")
        print(f"  The Guardian API pulled general news — only Hormuz-related ones pass the filter.")

    if all_good:
        print(f"  [PHASE 1 EXIT CRITERIA: PASSED]")
        print(f"  {len(inserted_results)} structured events extracted, vocabulary constrained, graph updated.")
    elif passed:
        print(f"  [PHASE 1 EXIT CRITERIA: PARTIAL PASS]")
        print(f"  Vocabulary containment: OK | Events inserted: {len(inserted_results)}/{NUM_ARTICLES}")
    else:
        print(f"  [PHASE 1 EXIT CRITERIA: FAILED]")
        print(f"  Fix the issues above before proceeding to Phase 2.")
    print(SEPARATOR)


if __name__ == "__main__":
    run_validation()
