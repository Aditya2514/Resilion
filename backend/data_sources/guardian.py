"""
Guardian Open Platform connector.
Source tier: TIER 3 — Full-text news articles (supporting context).

Free API key required: https://open-platform.theguardian.com/access/
Set GUARDIAN_API_KEY in environment or .env before using.

The Guardian is used to:
  - Pull recent full-text articles about energy, shipping, Iran sanctions
  - Provide article body text to the LLM extraction pipeline (Phase 1)
  - Build the historical archive for Phase 5 backtesting

IMPORTANT: Tier 3 source — never present a Guardian-only claim with the
same confidence as a Tier 1 (EIA/OFAC) fact. Confidence scoring accounts for
source tier (see config.py).
"""

import sys
import requests
from datetime import datetime, timedelta

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import GUARDIAN_API_KEY, GUARDIAN_API_BASE, TIER_3_SOURCES

DEFAULT_SEARCH_QUERY = "Strait of Hormuz OR Iran oil OR crude oil tanker OR shipping disruption OR OFAC sanctions"

HORMUZ_CRISIS_QUERY = "Strait of Hormuz OR Iran blockade OR oil tanker OR Bab-el-Mandeb"


def fetch_guardian_articles(
    query: str = DEFAULT_SEARCH_QUERY,
    show_fields: list[str] | None = None,
    from_date: str | None = None,   # YYYY-MM-DD
    to_date: str | None = None,
    page_size: int = 5,
    section: str | None = None,     # e.g. 'world', 'business', 'environment'
) -> dict:
    """
    Search Guardian Open Platform for recent energy/shipping articles.

    Args:
        query:       Search string (supports OR, AND, phrase)
        show_fields: Fields to include in response. Defaults to
                     ['headline', 'bodyText', 'webPublicationDate', 'webUrl', 'trailText']
        from_date:   Filter articles from this date (YYYY-MM-DD)
        to_date:     Filter articles to this date (YYYY-MM-DD)
        page_size:   Number of articles to return (max 50)
        section:     Restrict to a section (e.g. 'world')

    Returns:
        dict with keys: source, tier, fetched_at, query, data (list of article dicts), error (if any)
    """
    if show_fields is None:
        show_fields = ["headline", "bodyText", "webPublicationDate", "webUrl", "trailText", "wordcount"]

    if GUARDIAN_API_KEY == "INSERT_GUARDIAN_API_KEY_HERE":
        return {
            "source": "GUARDIAN",
            "tier": 3,
            "status": "NO_KEY",
            "message": "Set GUARDIAN_API_KEY environment variable. "
                        "Get a free key at https://open-platform.theguardian.com/access/",
            "data": [],
        }

    params: dict = {
        "q": query,
        "api-key": GUARDIAN_API_KEY,
        "show-fields": ",".join(show_fields),
        "page-size": page_size,
        "order-by": "newest",
    }

    if from_date:
        params["from-date"] = from_date
    if to_date:
        params["to-date"] = to_date
    if section:
        params["section"] = section

    endpoint = f"{GUARDIAN_API_BASE}/search"

    try:
        resp = requests.get(endpoint, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as e:
        return {
            "source": "GUARDIAN",
            "tier": 3,
            "status": "REQUEST_ERROR",
            "error": str(e),
            "query": query,
            "data": [],
        }

    results = payload.get("response", {}).get("results", [])
    parsed = []
    for r in results:
        fields = r.get("fields", {})
        body_text = fields.get("bodyText", "")
        parsed.append({
            "id": r.get("id", ""),
            "title": fields.get("headline", r.get("webTitle", "")),
            "url": r.get("webUrl", ""),
            "published_at": r.get("webPublicationDate", ""),
            "section": r.get("sectionName", ""),
            "trail_text": fields.get("trailText", ""),
            "body_text": body_text[:3000] if body_text else "",  # cap for storage
            "word_count": fields.get("wordcount", 0),
            "source": "GUARDIAN",
            "tier": 3,
        })

    return {
        "source": "GUARDIAN",
        "tier": 3,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "query": query,
        "total_returned": len(parsed),
        "total_available": payload.get("response", {}).get("total", 0),
        "data": parsed,
    }


def fetch_hormuz_crisis_articles(
    from_date: str = "2026-02-01",
    to_date: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    Pull Guardian articles covering the 2026 US-Iran / Strait of Hormuz crisis.
    Used to build the historical archive for Phase 5 backtesting.

    Args:
        from_date:  Start date YYYY-MM-DD (default: 2026-02-01 — crisis eruption)
        to_date:    End date YYYY-MM-DD (default: today)
        page_size:  Number of articles
    """
    if to_date is None:
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

    return fetch_guardian_articles(
        query=HORMUZ_CRISIS_QUERY,
        from_date=from_date,
        to_date=to_date,
        page_size=page_size,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Guardian Connector — Phase 0 Sample Pull")
    print("=" * 60)

    result = fetch_guardian_articles(page_size=3)
    print(f"\n[Guardian] Status: {result.get('status', 'OK')}")

    if result.get("status") == "NO_KEY":
        print(f"  ⚠  {result['message']}")
        print("  (Skipping Guardian — set key and re-run)")
    elif result.get("error"):
        print(f"  ✗  Error: {result['error']}")
    else:
        print(f"  ✓  Fetched {result['total_returned']} of {result['total_available']} articles")
        for art in result["data"]:
            pub = art["published_at"][:10] if art["published_at"] else "N/A"
            print(f"\n  [{pub}] {art['title'][:80]}")
            print(f"    Section: {art['section']} | Words: {art['word_count']}")
            print(f"    URL: {art['url'][:80]}")
            if art["trail_text"]:
                print(f"    Summary: {art['trail_text'][:120]}...")
