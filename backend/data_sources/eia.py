"""
EIA (U.S. Energy Information Administration) API connector.
Source tier: TIER 1 — Official government data, treated as ground truth.

API docs: https://www.eia.gov/opendata/documentation.php
Free key: https://www.eia.gov/opendata/register.php

Set EIA_API_KEY in environment or .env before using.
"""

import sys
import requests
from datetime import datetime, timedelta

# Allow running as a standalone script
if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import EIA_API_KEY, EIA_API_BASE, TIER_1_SOURCES


def fetch_crude_imports_sample(
    frequency: str = "monthly",
    data_fields: list[str] | None = None,
    num_records: int = 5,
) -> dict:
    """
    Pull a sample of US crude oil import volumes from EIA v2 API.

    Series: petroleum/imports/us — monthly crude import volumes by country of origin.
    Returns a dict with 'meta' and 'data' keys on success, or 'error' on failure.

    Args:
        frequency:   'monthly' (default) or 'annual'
        data_fields: list of data columns to request; defaults to ['value']
        num_records: how many most-recent records to fetch

    Returns:
        dict with keys: source, tier, fetched_at, endpoint, data (list of records), error (if any)
    """
    if data_fields is None:
        data_fields = ["value"]

    if EIA_API_KEY == "INSERT_EIA_API_KEY_HERE":
        return {
            "source": "EIA",
            "tier": 1,
            "status": "NO_KEY",
            "message": "Set EIA_API_KEY environment variable. "
                        "Get a free key at https://www.eia.gov/opendata/register.php",
            "data": [],
        }

    endpoint = f"{EIA_API_BASE}/petroleum/imports/us/data/"
    params = {
        "api_key": EIA_API_KEY,
        "frequency": frequency,
        "data[]": data_fields,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": num_records,
        "offset": 0,
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        return {
            "source": "EIA",
            "tier": 1,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "endpoint": endpoint,
            "data": payload.get("response", {}).get("data", []),
            "total_records": payload.get("response", {}).get("total", 0),
        }
    except requests.exceptions.HTTPError as e:
        return {"source": "EIA", "tier": 1, "status": "HTTP_ERROR", "error": str(e), "data": []}
    except requests.exceptions.RequestException as e:
        return {"source": "EIA", "tier": 1, "status": "REQUEST_ERROR", "error": str(e), "data": []}


def fetch_petroleum_prices(num_records: int = 5) -> dict:
    """
    Pull recent crude oil spot prices (WTI, Brent) from EIA.
    Useful for attaching price context to disruption events.
    """
    if EIA_API_KEY == "INSERT_EIA_API_KEY_HERE":
        return {
            "source": "EIA",
            "tier": 1,
            "status": "NO_KEY",
            "message": "Set EIA_API_KEY environment variable.",
            "data": [],
        }

    endpoint = f"{EIA_API_BASE}/petroleum/pri/spt/data/"
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "daily",
        "data[]": ["value"],
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": num_records,
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        return {
            "source": "EIA",
            "tier": 1,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "endpoint": endpoint,
            "data": payload.get("response", {}).get("data", []),
        }
    except requests.exceptions.RequestException as e:
        return {"source": "EIA", "tier": 1, "status": "REQUEST_ERROR", "error": str(e), "data": []}


if __name__ == "__main__":
    import json
    print("=" * 60)
    print("EIA Data Source — Phase 0 Sample Pull")
    print("=" * 60)

    result = fetch_crude_imports_sample(num_records=3)
    print(f"\n[EIA] Crude Import Volumes (status: {result.get('status', 'OK')})")

    if result.get("status") == "NO_KEY":
        print(f"  ⚠  {result['message']}")
    elif result.get("error"):
        print(f"  ✗  Error: {result['error']}")
    else:
        print(f"  ✓  Fetched {len(result['data'])} records")
        for rec in result["data"][:3]:
            print(f"     {rec}")

    prices = fetch_petroleum_prices(num_records=3)
    print(f"\n[EIA] Spot Prices (status: {prices.get('status', 'OK')})")
    if prices.get("status") == "NO_KEY":
        print(f"  ⚠  {prices['message']}")
    elif prices.get("error"):
        print(f"  ✗  Error: {prices['error']}")
    else:
        print(f"  ✓  Fetched {len(prices['data'])} records")
        for rec in prices["data"][:3]:
            print(f"     {rec}")
