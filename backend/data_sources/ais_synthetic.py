"""
Synthetic AIS (Automatic Identification System) / Tanker Position Data Generator.

!!! SYNTHETIC DATA — NOT LIVE AIS !!!
!!! This dataset is generated programmatically for development and demo purposes. !!!
!!! It is NOT connected to any real vessel tracking system.                       !!!
!!! Real AIS data requires a paid integration (e.g. MarineTraffic, Spire) which  !!!
!!! is explicitly out of scope for this build.                                    !!!
!!! Never present this data as live tracking to any audience.                     !!!

This synthetic dataset is used to:
  - Seed the graph with representative tanker nodes (Corridor → Vessel links)
  - Simulate what live AIS might look like for the demo (clearly labeled)
  - Provide realistic-looking disruption context (e.g. "12 tankers dark" in the Strait)

Generated data fields per vessel:
  - vessel_id:   IMO-style identifier (synthetic, not real IMO numbers)
  - name:        Fictional vessel name (format: [ELEMENT]-[NUMBER])
  - flag:        Country of registration (proportional to real tanker fleet composition)
  - type:        Vessel type (VLCC, Suezmax, Aframax, LNG)
  - corridor:    One of our 3 seeded corridors
  - lat/lon:     Position within realistic corridor bounding boxes
  - heading:     Direction in degrees
  - speed_knots: Speed in knots (0 = anchored/stopped)
  - status:      UNDERWAY | ANCHORED | DARK | DIVERTING | WAITING
  - timestamp:   Simulated observation time (recent, within last 48h)
  - cargo:       Crude oil, LNG, Refined products
  - destination: Port/region (from our seeded refinery list)
  - data_label:  Always "SYNTHETIC" — required field, do NOT remove
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import (
    CORRIDORS,
    REFINERIES,
    ALTERNATIVE_SUPPLIERS,
    SYNTHETIC_AIS_NUM_VESSELS,
    SYNTHETIC_AIS_OUTPUT_PATH,
)

# ── Corridor bounding boxes (lat_min, lat_max, lon_min, lon_max) ───────────────
CORRIDOR_BOUNDS: dict[str, dict] = {
    "Strait of Hormuz": {
        "lat": (25.5, 26.8),
        "lon": (56.0, 57.5),
        "typical_heading": (260, 100),   # (inbound, outbound)
        "typical_speed": (10, 15),
    },
    "Bab-el-Mandeb / Red Sea corridor": {
        "lat": (11.5, 13.5),
        "lon": (43.0, 45.0),
        "typical_heading": (320, 150),
        "typical_speed": (10, 14),
    },
    "Strait of Malacca": {
        "lat": (1.0, 4.0),
        "lon": (103.5, 104.5),
        "typical_heading": (310, 130),
        "typical_speed": (10, 16),
    },
}

VESSEL_TYPES = ["VLCC", "Suezmax", "Aframax", "LNG Carrier", "Product Tanker"]
VESSEL_TYPE_WEIGHTS = [0.35, 0.25, 0.20, 0.10, 0.10]

FLAGS = ["Marshall Islands", "Panama", "Liberia", "Greece", "Bahamas", "Malta", "UAE", "Singapore"]
FLAG_WEIGHTS = [0.20, 0.18, 0.15, 0.12, 0.12, 0.08, 0.08, 0.07]

CARGOS = ["Crude Oil", "Crude Oil", "Crude Oil", "LNG", "Refined Products"]

VESSEL_NAME_ELEMENTS = [
    "ATLAS", "TITAN", "POSEIDON", "TRITON", "KRONOS",
    "HERMES", "ARES", "ORION", "HELIOS", "ZEUS",
    "NOVA", "VEGA", "LYRA", "CETUS", "HYDRA",
    "CASPIAN", "ARABIAN", "GULF", "INDIAN", "PACIFIC",
]

STATUS_WEIGHTS_NORMAL = {
    "UNDERWAY": 0.60,
    "ANCHORED": 0.15,
    "DARK": 0.10,       # transponder off — suspicious / sanctions evasion
    "DIVERTING": 0.10,
    "WAITING": 0.05,
}

STATUS_WEIGHTS_CRISIS = {
    "UNDERWAY": 0.25,
    "ANCHORED": 0.20,
    "DARK": 0.35,       # far more dark vessels during Hormuz blockade
    "DIVERTING": 0.15,
    "WAITING": 0.05,
}

# Proportional distribution of vessels across corridors
# Crisis: Hormuz heavily disrupted, more vessels diverting
CORRIDOR_DISTRIBUTION_CRISIS = {
    "Strait of Hormuz": 0.55,
    "Bab-el-Mandeb / Red Sea corridor": 0.25,
    "Strait of Malacca": 0.20,
}


def generate_synthetic_ais(
    num_vessels: int = SYNTHETIC_AIS_NUM_VESSELS,
    crisis_mode: bool = True,   # True = Hormuz crisis status distribution
    seed: int = 42,             # Reproducible generation
) -> list[dict]:
    """
    Generate a synthetic AIS dataset representing tanker traffic across
    our three seeded corridors, reflecting the 2026 Hormuz crisis conditions.

    IMPORTANT: All returned records include data_label="SYNTHETIC".
    This field must NEVER be stripped or hidden in any downstream processing or UI.

    Args:
        num_vessels: Number of synthetic vessel records to generate
        crisis_mode: If True, use disrupted status distribution (more DARK vessels)
        seed:        Random seed for reproducibility

    Returns:
        List of vessel dicts, each with data_label="SYNTHETIC"
    """
    random.seed(seed)
    now = datetime.utcnow()

    status_weights = STATUS_WEIGHTS_CRISIS if crisis_mode else STATUS_WEIGHTS_NORMAL
    corridor_dist = CORRIDOR_DISTRIBUTION_CRISIS

    vessels = []
    vessel_num = 1000  # Starting synthetic vessel number

    # Assign corridors by distribution
    corridor_assignments = []
    for corridor, fraction in corridor_dist.items():
        count = round(fraction * num_vessels)
        corridor_assignments.extend([corridor] * count)
    # Fill remainder with Hormuz
    while len(corridor_assignments) < num_vessels:
        corridor_assignments.append("Strait of Hormuz")
    corridor_assignments = corridor_assignments[:num_vessels]
    random.shuffle(corridor_assignments)

    for i in range(num_vessels):
        corridor = corridor_assignments[i]
        bounds = CORRIDOR_BOUNDS[corridor]

        # Position within corridor bounds
        lat = round(random.uniform(*bounds["lat"]), 5)
        lon = round(random.uniform(*bounds["lon"]), 5)

        # Status and speed
        status = random.choices(
            list(status_weights.keys()),
            weights=list(status_weights.values()),
            k=1,
        )[0]
        speed = 0.0 if status in ("ANCHORED", "DARK", "WAITING") else round(
            random.uniform(*bounds["typical_speed"]), 1
        )
        heading = random.choice(bounds["typical_heading"]) + random.randint(-20, 20)
        heading = heading % 360

        # Timestamp within last 48h (simulated observation)
        obs_offset_hours = random.uniform(0, 47)
        timestamp = (now - timedelta(hours=obs_offset_hours)).isoformat() + "Z"

        vessel_type = random.choices(VESSEL_TYPES, weights=VESSEL_TYPE_WEIGHTS, k=1)[0]
        flag = random.choices(FLAGS, weights=FLAG_WEIGHTS, k=1)[0]
        cargo = random.choice(CARGOS)
        name_element = random.choice(VESSEL_NAME_ELEMENTS)
        vessel_name = f"MT {name_element} {vessel_num + i}"

        # Destination: one of our seeded refineries or "UNKNOWN" (dark vessels often have unknown dest)
        if status == "DARK":
            destination = "UNKNOWN"
        else:
            dest_pool = REFINERIES + ["Fujairah, UAE", "Singapore", "Port Said, Egypt", "Unknown"]
            destination = random.choice(dest_pool)

        # For DIVERTING vessels, add a divert_reason
        divert_reason = None
        if status == "DIVERTING":
            divert_reason = random.choice([
                "Hormuz blockade — rerouting via Cape of Good Hope",
                "Red Sea attack risk — rerouting via Suez northbound",
                "Sanctions compliance check — awaiting clearance",
                "Charter amendment — destination change in progress",
            ])

        vessel: dict = {
            "vessel_id": f"SYN-IMO-{9000000 + i:07d}",   # SYN- prefix marks as synthetic
            "name": vessel_name,
            "flag": flag,
            "type": vessel_type,
            "corridor": corridor,
            "lat": lat,
            "lon": lon,
            "heading_deg": heading,
            "speed_knots": speed,
            "status": status,
            "cargo": cargo,
            "destination": destination,
            "timestamp": timestamp,
            "crisis_mode": crisis_mode,
            # !! REQUIRED FIELD — do NOT remove or set to anything else !!
            "data_label": "SYNTHETIC",
            "data_label_note": (
                "This is programmatically generated data for development/demo. "
                "NOT connected to any real AIS tracking system. "
                "Do not present as live vessel positions."
            ),
        }

        if divert_reason:
            vessel["divert_reason"] = divert_reason

        vessels.append(vessel)

    return vessels


def save_synthetic_ais(
    output_path: Path = SYNTHETIC_AIS_OUTPUT_PATH,
    num_vessels: int = SYNTHETIC_AIS_NUM_VESSELS,
    crisis_mode: bool = True,
) -> Path:
    """
    Generate and save the synthetic AIS dataset to JSON.
    Returns the path to the saved file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vessels = generate_synthetic_ais(num_vessels=num_vessels, crisis_mode=crisis_mode)

    output = {
        "data_label": "SYNTHETIC",
        "data_label_note": (
            "Programmatically generated tanker positions for Resilion demo purposes. "
            "NOT live AIS data. Real AIS requires a paid integration (MarineTraffic, Spire). "
            "Do not present as live data."
        ),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "crisis_mode": crisis_mode,
        "crisis_context": "2026 US-Iran Strait of Hormuz crisis (Feb 2026 – present)",
        "num_vessels": len(vessels),
        "vessels": vessels,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("Synthetic AIS Generator — Phase 0")
    print("!!! SYNTHETIC DATA — NOT LIVE AIS !!!")
    print("=" * 60)

    path = save_synthetic_ais()

    # Print summary
    with open(path) as f:
        data = json.load(f)

    vessels = data["vessels"]
    print(f"\n  ✓  Generated {len(vessels)} synthetic vessel records")
    print(f"  ✓  Saved to: {path}")
    print(f"  ✓  data_label: {data['data_label']}  ← always present")
    print(f"\n  Status distribution:")
    from collections import Counter
    status_counts = Counter(v["status"] for v in vessels)
    for status, count in sorted(status_counts.items()):
        print(f"    {status:12s}: {count:3d} vessels")

    print(f"\n  Corridor distribution:")
    corridor_counts = Counter(v["corridor"] for v in vessels)
    for corridor, count in sorted(corridor_counts.items()):
        print(f"    {count:3d} vessels — {corridor}")

    print(f"\n  Sample vessel (first entry):")
    v = vessels[0]
    for k, val in v.items():
        if k != "data_label_note":
            print(f"    {k:20s}: {val}")
