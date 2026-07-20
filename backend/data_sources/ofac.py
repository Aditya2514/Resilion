"""
OFAC (Office of Foreign Assets Control) Sanctions List connector.
Source tier: TIER 1 — Official US Treasury designation data, ground truth.

Data source: US Treasury public CDN — no API key required, no scraping.
  - Consolidated Sanctions List (XML): publicly available at sanctionslistservice.ofac.treas.gov
  - Fallback: SDN XML at treasury.gov/ofac/downloads/sdn.xml

OFAC designations are used to:
  - Tag sanctioned entities (tankers, companies, individuals) as Sanction nodes in the graph
  - Block or flag recommended alternative suppliers/routes that involve sanctioned parties
  - Wire TARGETS edges: Sanction → Corridor/Refinery/Supplier
"""

import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import OFAC_CONSOLIDATED_URL, OFAC_SDN_XML_URL


# Energy / shipping-relevant OFAC program codes to filter for
ENERGY_PROGRAMS = {
    "IRAN", "IRAN-EO13846", "IRAN-TRA", "IRGC",
    "RUSSIA-EO14024", "RUSSIA-EO14066", "SDN",
    "SDGT", "NPWMD", "SDNTK",
}

# Keywords to identify energy/shipping-relevant designations
SHIPPING_KEYWORDS = {
    "tanker", "vessel", "shipping", "petroleum", "crude", "oil",
    "refinery", "energy", "maritime", "cargo", "lng", "pipeline",
}


def fetch_ofac_sdn_sample(max_records: int = 10, filter_energy: bool = True) -> dict:
    """
    Fetch a sample from the OFAC SDN (Specially Designated Nationals) XML list.

    Attempts the Consolidated XML first (more complete), falls back to the
    classic SDN XML if that fails. Filters for energy/shipping-relevant
    designations by default.

    Args:
        max_records:    Maximum number of designation records to return
        filter_energy:  If True, return only energy/maritime-relevant entries

    Returns:
        dict with keys: source, tier, fetched_at, total_scanned, data (list of dicts), error (if any)
    """
    urls_to_try = [OFAC_CONSOLIDATED_URL, OFAC_SDN_XML_URL]

    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Resilion-Research/1.0"})
            resp.raise_for_status()
            return _parse_sdn_xml(resp.content, url, max_records, filter_energy)
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            continue

    return {
        "source": "OFAC",
        "tier": 1,
        "status": "REQUEST_ERROR",
        "error": last_error,
        "data": [],
    }


def _parse_sdn_xml(xml_bytes: bytes, url: str, max_records: int, filter_energy: bool) -> dict:
    """Parse OFAC SDN XML and extract designation records."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return {"source": "OFAC", "tier": 1, "status": "PARSE_ERROR", "error": str(e), "data": []}

    # OFAC XML uses a namespace — strip it for simple access
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    records = []
    total_scanned = 0

    # Try both SDN and Consolidated XML element names
    entry_tags = [f"{ns}sdnEntry", f"{ns}entry", "sdnEntry", "entry"]

    entries = []
    for tag in entry_tags:
        entries = root.findall(f".//{tag}")
        if entries:
            break

    for entry in entries:
        total_scanned += 1

        def get_text(tag: str) -> str:
            el = entry.find(f"{ns}{tag}") or entry.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        uid = get_text("uid")
        last_name = get_text("lastName")
        first_name = get_text("firstName")
        entity_type = get_text("sdnType")  # Individual, Entity, Vessel, Aircraft
        program = get_text("program")
        title = get_text("title")
        remarks = get_text("remarks")

        full_name = f"{first_name} {last_name}".strip() if first_name else last_name

        # Filter: energy/shipping programs or keywords in name/title/remarks
        if filter_energy:
            program_match = any(p in program.upper() for p in ENERGY_PROGRAMS)
            keyword_blob = f"{full_name} {title} {remarks}".lower()
            keyword_match = any(kw in keyword_blob for kw in SHIPPING_KEYWORDS)
            if not (program_match or keyword_match):
                continue

        record = {
            "uid": uid,
            "name": full_name,
            "entity_type": entity_type,
            "program": program,
            "title": title,
            "remarks": remarks[:200] if remarks else "",
            "source_url": url,
        }
        records.append(record)

        if len(records) >= max_records:
            break

    return {
        "source": "OFAC",
        "tier": 1,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source_url": url,
        "total_scanned": total_scanned,
        "total_matched": len(records),
        "data": records,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("OFAC Sanctions Connector — Phase 0 Sample Pull")
    print("=" * 60)
    result = fetch_ofac_sdn_sample(max_records=5, filter_energy=True)

    print(f"\n[OFAC] Status: {result.get('status', 'OK')}")
    if result.get("error"):
        print(f"  ✗  Error: {result['error']}")
    else:
        print(f"  ✓  Scanned {result.get('total_scanned', '?')} entries")
        print(f"  ✓  Matched {result.get('total_matched', 0)} energy/shipping-relevant designations")
        print(f"  ✓  Fetched at: {result.get('fetched_at', 'N/A')}\n")
        for r in result["data"]:
            print(f"  [{r['entity_type']}] {r['name']} — Program: {r['program']}")
            if r["title"]:
                print(f"    Title: {r['title']}")
            if r["remarks"]:
                print(f"    Remarks: {r['remarks'][:100]}...")
            print()
