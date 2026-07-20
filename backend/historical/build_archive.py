"""
Historical archive builder — 2026 US-Iran / Strait of Hormuz crisis.

Pulls GDELT events and (optionally) Guardian articles from the ongoing
Strait of Hormuz crisis (Feb 2026 → present) for Phase 5 backtesting.

Crisis phases:
  - eruption   (Feb 01 – Mar 15, 2026): Hostilities erupt, Brent ~$110, ~8M bbl/day disrupted
  - escalation (Mar 16 – Jun 30, 2026): Sustained disruption, dark tanker crossings
  - blockade   (Jul 01 – Jul 19, 2026): US reinstates blockade Jul 14, 20% cargo fee, Brent +9.5%
  - ongoing    (Jul 14 – present):       US-Iran still trading attacks, traffic sharply reduced

Output: backend/historical/events_2026_hormuz_crisis.json

Each record is tagged with:
  - source: GDELT or GUARDIAN
  - date: ISO date string
  - url: article URL
  - title: article title
  - raw_text: article body (or snippet)
  - crisis_phase: eruption | escalation | blockade | ongoing
  - tier: 2 (GDELT) or 3 (Guardian)
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from config import HISTORICAL_DIR, CRISIS_PHASES
from data_sources.gdelt import fetch_gdelt_articles, HORMUZ_CRISIS_QUERY
from data_sources.guardian import fetch_hormuz_crisis_articles


OUTPUT_PATH = HISTORICAL_DIR / "events_2026_hormuz_crisis.json"

# GDELT date format: YYYYMMDDHHMMSS
# Config dates: YYYY-MM-DD
def date_to_gdelt(date_str: str, end_of_day: bool = False) -> str:
    """Convert YYYY-MM-DD to YYYYMMDDHHMMSS for GDELT API."""
    date_str = date_str.replace("-", "")
    suffix = "235959" if end_of_day else "000000"
    return f"{date_str}{suffix}"


def build_archive(
    max_per_phase: int = 15,
    include_guardian: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Pull and assemble the historical crisis archive from GDELT (and optionally Guardian).

    Args:
        max_per_phase:      Max GDELT articles per crisis phase
        include_guardian:   Whether to also pull Guardian articles (requires API key)
        verbose:            Print progress

    Returns:
        The complete archive dict (also saved to OUTPUT_PATH)
    """
    all_records = []
    stats = {}

    for phase_name, (start_date, end_date) in CRISIS_PHASES.items():
        if verbose:
            print(f"\n[Archive] Fetching phase: {phase_name} ({start_date} → {end_date})")

        # GDELT pull for this phase window
        gdelt_result = fetch_gdelt_articles(
            query=HORMUZ_CRISIS_QUERY,
            mode="ArtList",
            max_records=max_per_phase,
            start_date=date_to_gdelt(start_date),
            end_date=date_to_gdelt(end_date, end_of_day=True),
            sort="DateDesc",
        )

        phase_records = []
        for art in gdelt_result.get("data", []):
            # Parse GDELT date YYYYMMDDTHHMMSSZ → ISO
            raw_date = art.get("seendate", "")
            try:
                parsed_date = datetime.strptime(raw_date, "%Y%m%dT%H%M%SZ").isoformat() + "Z"
            except ValueError:
                parsed_date = raw_date

            record = {
                "source": "GDELT",
                "tier": 2,
                "crisis_phase": phase_name,
                "title": art.get("title", ""),
                "url": art.get("url", ""),
                "date": parsed_date,
                "domain": art.get("domain", ""),
                "tone": art.get("tone"),
                "raw_text": None,   # Phase 1 will fetch full text via trafilatura
                "metadata": {
                    "language": art.get("language", ""),
                    "sourcecountry": art.get("sourcecountry", ""),
                },
            }
            phase_records.append(record)

        if verbose:
            print(f"  GDELT: {len(phase_records)} articles fetched")
            if gdelt_result.get("error"):
                print(f"  ⚠ GDELT error: {gdelt_result['error']}")

        all_records.extend(phase_records)
        stats[phase_name] = {"gdelt": len(phase_records), "guardian": 0}

        # Longer pause between phases — GDELT's free tier rate-limits
        # rapid sequential calls. 5s is conservative; reduces 429s significantly.
        time.sleep(5.0)

    # Guardian pull (covers full window in one call if key is available)
    if include_guardian:
        if verbose:
            print(f"\n[Archive] Fetching Guardian articles (full crisis window)...")
        guardian_result = fetch_hormuz_crisis_articles(
            from_date="2026-02-01",
            page_size=20,
        )

        if guardian_result.get("status") == "NO_KEY":
            if verbose:
                print(f"  ⚠ Guardian: no API key — skipping (set GUARDIAN_API_KEY to include)")
        elif guardian_result.get("error"):
            if verbose:
                print(f"  ⚠ Guardian error: {guardian_result['error']}")
        else:
            guardian_records = []
            for art in guardian_result.get("data", []):
                pub_date = art.get("published_at", "")
                # Determine crisis phase from date
                phase = _classify_crisis_phase(pub_date)
                record = {
                    "source": "GUARDIAN",
                    "tier": 3,
                    "crisis_phase": phase,
                    "title": art.get("title", ""),
                    "url": art.get("url", ""),
                    "date": pub_date,
                    "raw_text": art.get("body_text") or art.get("trail_text", ""),
                    "metadata": {
                        "section": art.get("section", ""),
                        "word_count": art.get("word_count", 0),
                    },
                }
                guardian_records.append(record)
                phase_key = phase or "unknown"
                if phase_key in stats:
                    stats[phase_key]["guardian"] = stats[phase_key].get("guardian", 0) + 1

            # ─── BUG FIX: extend all_records with the collected Guardian articles ───
            all_records.extend(guardian_records)
            if verbose:
                print(f"  Guardian: {len(guardian_records)} articles fetched")

    # ── Post-fetch integrity check ──────────────────────────────────────────────
    # If no real data was collected, ABORT loudly — do not substitute fabricated content.
    # The old silent fallback (writing agent-invented text as real sourced records) has
    # been removed. A Phase 5 backtest on invented data would be worse than no backtest.
    if not all_records:
        print("\n" + "=" * 65)
        print("[Archive] ABORTED — 0 real records collected.")
        print("  GDELT: likely rate-limited across all phase windows.")
        print("  Guardian: check GUARDIAN_API_KEY is set in your .env file.")
        print("\n  Resolution options:")
        print("    1. Wait ~10 min and retry (GDELT rate limit resets)")
        print("    2. Set GUARDIAN_API_KEY in .env (key already fetched 20 articles)")
        print("    3. Pass --gdelt-only or --guardian-only flags to isolate sources")
        print("\n  DO NOT pass --force-seed. That flag writes fabricated placeholder")
        print("  text and labels it as sourced data — which inverts the project's")
        print("  entire credibility premise.")
        print("=" * 65)
        # Save an empty archive so the file exists and is clearly marked
        archive = {
            "archive_label": "2026_HORMUZ_CRISIS",
            "description": "INCOMPLETE — live fetch failed. Re-run with valid API keys and/or after GDELT rate limit resets.",
            "crisis_window": {"start": "2026-02-01", "end": datetime.utcnow().strftime("%Y-%m-%d"), "status": "ONGOING"},
            "built_at": datetime.utcnow().isoformat() + "Z",
            "total_records": 0,
            "data_integrity": "INCOMPLETE",
            "stats_by_phase": stats,
            "records": [],
        }
        HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)
        return archive

    # Build final archive
    sources_used = list({r["source"] for r in all_records})
    archive = {
        "archive_label": "2026_HORMUZ_CRISIS",
        "description": (
            "Real news events from the 2026 US-Iran / Strait of Hormuz crisis. "
            "For Phase 5 backtesting of the Resilion risk intelligence pipeline. "
            "Crisis is ONGOING as of archive build date."
        ),
        "crisis_window": {
            "start": "2026-02-01",
            "end": datetime.utcnow().strftime("%Y-%m-%d"),
            "status": "ONGOING",
        },
        "crisis_context": {
            "eruption": "Feb/Mar 2026: US-Iran hostilities erupt, virtual Strait of Hormuz shutdown, Brent crude near $110/bbl, ~8M bbl/day unavailable",
            "escalation": "Mar-Jun 2026: Sustained disruption, tanker 'dark' crossings, insurance premiums surge",
            "blockade": "Jul 14, 2026: US reinstates Strait of Hormuz blockade, 20% cargo fee imposed, Brent +9.5% above $83",
            "ongoing": "Jul 2026: US-Iran still trading attacks, maritime traffic sharply reduced",
        },
        "built_at": datetime.utcnow().isoformat() + "Z",
        "total_records": len(all_records),
        "data_integrity": "REAL",   # Explicitly distinguishes live-fetched from fabricated data
        "sources_used": sources_used,
        "stats_by_phase": stats,
        "records": all_records,
    }

    # Save
    HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"\n[Archive] ✓ Saved {len(all_records)} total records to: {OUTPUT_PATH}")
        print(f"[Archive] Stats by phase:")
        for phase, s in stats.items():
            print(f"  {phase:12s}: GDELT={s.get('gdelt',0)}, Guardian={s.get('guardian',0)}")

    return archive


def _classify_crisis_phase(date_str: str) -> str:
    """Classify a date string (ISO 8601) into a crisis_phase label."""
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        d = dt.date()
        import datetime as dt_module
        if d >= dt_module.date(2026, 7, 14):
            return "ongoing"
        elif d >= dt_module.date(2026, 7, 1):
            return "blockade"
        elif d >= dt_module.date(2026, 3, 16):
            return "escalation"
        elif d >= dt_module.date(2026, 2, 1):
            return "eruption"
        else:
            return "pre_crisis"
    except Exception:
        return "unknown"


if __name__ == "__main__":
    print("=" * 60)
    print("Historical Archive Builder — 2026 Hormuz Crisis")
    print("=" * 60)
    archive = build_archive(max_per_phase=15, include_guardian=True, verbose=True)
    print(f"\n✓ Archive complete. {archive['total_records']} records ready for Phase 5.")
