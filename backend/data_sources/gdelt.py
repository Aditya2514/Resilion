"""
GDELT 2.0 Document API connector.
Source tier: TIER 2 — Structured global event data (corroborated signal).

No API key required. Free public endpoint.
API docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

GDELT is used to:
  - Pull recent news articles matching energy/shipping/sanctions keywords
  - Extract structured event metadata (date, country, tone, domain)
  - Feed the Risk Intelligence Agent (Phase 1) with article text for LLM extraction
  - Build the historical archive for Phase 5 backtesting

GDELT DOC API response modes used here:
  - ArtList: structured article list with metadata (no full text, just URL+title+date+tone)
  - We then use trafilatura (see rss.py) to fetch full text from URLs if needed
"""

import sys
import json
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import GDELT_DOC_API_BASE

# ── Energy / Strait of Hormuz focused queries ──────────────────────────────────
DEFAULT_QUERY_TERMS = (
    '("Strait of Hormuz" OR "Bab-el-Mandeb" OR "Red Sea" OR "crude oil" OR '
    '"tanker" OR "shipping" OR "Iran sanctions" OR "oil blockade") '
    'sourcelang:English'
)

HORMUZ_CRISIS_QUERY = (
    '("Strait of Hormuz" OR "Iran blockade" OR "oil tanker" OR "crude oil" OR '
    '"shipping disruption" OR "maritime attack") sourcelang:English'
)


def fetch_gdelt_articles(
    query: str = DEFAULT_QUERY_TERMS,
    mode: str = "ArtList",
    max_records: int = 10,
    timespan: str = "2d",   # e.g. '1d', '7d', '1m' — or use start/end dates
    start_date: str | None = None,   # YYYYMMDDHHMMSS
    end_date: str | None = None,
    sort: str = "DateDesc",
) -> dict:
    """
    Query the GDELT 2.0 DOC API for recent energy/shipping news articles.

    Args:
        query:       GDELT query string (supports boolean operators)
        mode:        'ArtList' (article list) or 'TimelineVolInfo' (timeline)
        max_records: Max articles to return (GDELT caps at 250)
        timespan:    Relative time window — '1d', '7d', '1m', etc.
        start_date:  Absolute start date YYYYMMDDHHMMSS (overrides timespan)
        end_date:    Absolute end date YYYYMMDDHHMMSS
        sort:        'DateDesc' or 'ToneDesc' or 'HybridRel'

    Returns:
        dict with keys: source, tier, fetched_at, query, data (list of article dicts), error (if any)
    """
    params: dict = {
        "query": query,
        "mode": mode,
        "maxrecords": max_records,
        "sort": sort,
        "format": "json",
    }

    if start_date and end_date:
        params["startdatetime"] = start_date
        params["enddatetime"] = end_date
    else:
        params["timespan"] = timespan

    try:
        resp = requests.get(GDELT_DOC_API_BASE, params=params, timeout=20)
        resp.raise_for_status()
        raw = resp.json()
    except requests.exceptions.JSONDecodeError:
        # GDELT sometimes returns empty body for no results
        return {
            "source": "GDELT",
            "tier": 2,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "query": query,
            "data": [],
            "note": "GDELT returned empty response (no matching articles for this window)",
        }
    except requests.exceptions.RequestException as e:
        return {
            "source": "GDELT",
            "tier": 2,
            "status": "REQUEST_ERROR",
            "error": str(e),
            "query": query,
            "data": [],
        }

    articles = raw.get("articles", [])
    parsed = []
    for art in articles[:max_records]:
        parsed.append({
            "url": art.get("url", ""),
            "title": art.get("title", ""),
            "seendate": art.get("seendate", ""),        # YYYYMMDDTHHMMSSZ
            "domain": art.get("domain", ""),
            "language": art.get("language", ""),
            "sourcecountry": art.get("sourcecountry", ""),
            "tone": art.get("tone", None),              # negative = negative sentiment
            "image": art.get("image", ""),
            "source": "GDELT",
            "tier": 2,
        })

    return {
        "source": "GDELT",
        "tier": 2,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "query": query,
        "total_returned": len(parsed),
        "data": parsed,
    }


def fetch_hormuz_crisis_archive(
    start_date: str = "20260201000000",
    end_date: str | None = None,
    max_records: int = 50,
) -> dict:
    """
    Pull GDELT articles covering the 2026 US-Iran / Strait of Hormuz crisis.
    Used to build the historical archive for Phase 5 backtesting.

    Crisis window: Feb 2026 → present (ongoing as of July 2026).
    - Feb/Mar 2026: virtual Strait of Hormuz shutdown, Brent ~$110, ~8M bbl/day disrupted
    - July 14, 2026: US reinstates blockade with 20% cargo fee, Brent +9.5%

    Args:
        start_date: Archive start in YYYYMMDDHHMMSS (default: 2026-02-01)
        end_date:   Archive end in YYYYMMDDHHMMSS (default: now)
        max_records: Max articles per query (GDELT caps at 250)

    Returns:
        Combined dict of articles from multiple query windows
    """
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    return fetch_gdelt_articles(
        query=HORMUZ_CRISIS_QUERY,
        mode="ArtList",
        max_records=max_records,
        start_date=start_date,
        end_date=end_date,
        sort="DateDesc",
    )


if __name__ == "__main__":
    print("=" * 60)
    print("GDELT Connector — Phase 0 Sample Pull")
    print("=" * 60)

    # Live sample (last 2 days)
    print("\n[GDELT] Live sample — last 2 days (energy/shipping keywords):")
    result = fetch_gdelt_articles(timespan="2d", max_records=5)
    print(f"  Status: {result.get('status', 'OK')}")
    if result.get("error"):
        print(f"  ✗  Error: {result['error']}")
    else:
        print(f"  ✓  Fetched {result['total_returned']} articles")
        for art in result["data"]:
            date_str = art["seendate"][:8] if art["seendate"] else "N/A"
            print(f"  [{date_str}] {art['title'][:80]}")
            print(f"    Domain: {art['domain']} | Tone: {art.get('tone', 'N/A')}")
            print(f"    URL: {art['url'][:80]}")
            print()

    # Historical archive sample (Hormuz crisis)
    print("\n[GDELT] Hormuz crisis archive sample (Feb 2026 – Jul 2026):")
    archive = fetch_hormuz_crisis_archive(
        start_date="20260201000000",
        max_records=5,
    )
    print(f"  Status: {archive.get('status', 'OK')}")
    if archive.get("error"):
        print(f"  ✗  Error: {archive['error']}")
    else:
        print(f"  ✓  Fetched {archive['total_returned']} articles from crisis window")
        for art in archive["data"]:
            date_str = art["seendate"][:8] if art["seendate"] else "N/A"
            print(f"  [{date_str}] {art['title'][:80]}")
