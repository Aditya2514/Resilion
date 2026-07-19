"""
RSS Feed connector with trafilatura full-text extraction.
Source tier: TIER 3 — Trade press / news (supporting context only).

No API key required for public RSS feeds.
Uses:
  - feedparser: parse RSS/Atom feeds
  - trafilatura: extract clean article body from fetched HTML

Feeds configured in config.py (RSS_FEEDS dict).
Primary feed for Phase 0: EIA Today In Energy RSS (no paywall).

IMPORTANT: Tier 3 source — treat as supporting context, not ground truth.
Never present an RSS-only claim with the same confidence as a Tier 1 source.
"""

import sys
import requests
from datetime import datetime
from urllib.error import URLError

import feedparser

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    print("Warning: trafilatura not installed — full text extraction will be skipped.")
    print("Run: pip install trafilatura")

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import RSS_FEEDS, PRIMARY_RSS_FEED, TIER_3_SOURCES


def fetch_rss_feed(
    feed_name: str = PRIMARY_RSS_FEED,
    feed_url: str | None = None,
    max_entries: int = 5,
    fetch_full_text: bool = True,
    full_text_max_chars: int = 4000,
) -> dict:
    """
    Parse an RSS feed and optionally extract full article text via trafilatura.

    Args:
        feed_name:           Key in RSS_FEEDS dict (used if feed_url is None)
        feed_url:            Direct URL override (overrides feed_name lookup)
        max_entries:         How many entries to return
        fetch_full_text:     Whether to fetch + extract full body text for the first entry
        full_text_max_chars: Cap on extracted body text length (for storage)

    Returns:
        dict with keys: source, tier, feed_name, feed_url, fetched_at,
                        data (list of entry dicts), error (if any)
    """
    url = feed_url or RSS_FEEDS.get(feed_name)
    if not url:
        return {
            "source": "RSS",
            "tier": 3,
            "status": "CONFIG_ERROR",
            "error": f"Unknown feed name: {feed_name}. Available: {list(RSS_FEEDS.keys())}",
            "data": [],
        }

    try:
        parsed = feedparser.parse(url)
    except Exception as e:
        return {
            "source": "RSS",
            "tier": 3,
            "status": "PARSE_ERROR",
            "error": str(e),
            "feed_name": feed_name,
            "feed_url": url,
            "data": [],
        }

    if parsed.bozo and not parsed.entries:
        return {
            "source": "RSS",
            "tier": 3,
            "status": "FEED_ERROR",
            "error": f"feedparser bozo error: {parsed.bozo_exception}",
            "feed_name": feed_name,
            "feed_url": url,
            "data": [],
        }

    entries = []
    for i, entry in enumerate(parsed.entries[:max_entries]):
        entry_url = entry.get("link", "")
        published = entry.get("published", entry.get("updated", ""))

        record: dict = {
            "title": entry.get("title", ""),
            "url": entry_url,
            "published": published,
            "summary": entry.get("summary", "")[:500],
            "tags": [t.term for t in entry.get("tags", [])],
            "source": f"RSS_{feed_name.upper()}",
            "tier": 3,
            "full_text": None,
            "full_text_chars": 0,
        }

        # Only fetch full text for the first entry (exit criteria demo)
        if fetch_full_text and i == 0 and entry_url and HAS_TRAFILATURA:
            full_text = _extract_full_text(entry_url, max_chars=full_text_max_chars)
            record["full_text"] = full_text
            record["full_text_chars"] = len(full_text) if full_text else 0

        entries.append(record)

    return {
        "source": "RSS",
        "tier": 3,
        "feed_name": feed_name,
        "feed_url": url,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "feed_title": parsed.feed.get("title", ""),
        "total_entries_in_feed": len(parsed.entries),
        "total_returned": len(entries),
        "trafilatura_available": HAS_TRAFILATURA,
        "data": entries,
    }


def _extract_full_text(url: str, max_chars: int = 4000) -> str | None:
    """
    Fetch a URL and extract clean article body text using trafilatura.
    Returns None if extraction fails or trafilatura is unavailable.
    """
    if not HAS_TRAFILATURA:
        return None
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        if text and max_chars:
            text = text[:max_chars]
        return text
    except Exception:
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("RSS Feed Connector — Phase 0 Sample Pull")
    print("=" * 60)

    print(f"\n[RSS] Parsing feed: {PRIMARY_RSS_FEED} ({RSS_FEEDS.get(PRIMARY_RSS_FEED)})")
    result = fetch_rss_feed(feed_name=PRIMARY_RSS_FEED, max_entries=3, fetch_full_text=True)

    print(f"  Status: {result.get('status', 'OK')}")
    if result.get("error"):
        print(f"  ✗  Error: {result['error']}")
    else:
        print(f"  ✓  Feed title: {result.get('feed_title', 'N/A')}")
        print(f"  ✓  Entries in feed: {result.get('total_entries_in_feed', '?')}")
        print(f"  ✓  trafilatura: {'available' if result['trafilatura_available'] else 'NOT installed'}")
        print()

        for i, entry in enumerate(result["data"]):
            pub = entry.get("published", "N/A")[:20]
            print(f"  [{pub}] {entry['title'][:80]}")
            print(f"    URL: {entry['url'][:80]}")
            if entry.get("full_text"):
                print(f"    Full text extracted: {entry['full_text_chars']} chars")
                print(f"    Preview: {entry['full_text'][:200]}...")
            elif i == 0:
                print("    Full text: not extracted (trafilatura unavailable or fetch failed)")
            print()
