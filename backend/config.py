"""
Resilion — Central configuration and API key management.
All secrets are read from environment variables or a local .env file.
Never commit real keys to this file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Project root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = Path(__file__).parent
DATA_DIR = BACKEND_ROOT / "data"
HISTORICAL_DIR = BACKEND_ROOT / "historical"
GRAPH_STATE_PATH = BACKEND_ROOT / "graph_state.json"

# Load environment variables from .env in project root
load_dotenv(PROJECT_ROOT / ".env")

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
HISTORICAL_DIR.mkdir(exist_ok=True)

# ── API Keys (set via environment variables) ──────────────────────────────────
EIA_API_KEY = os.getenv("EIA_API_KEY", "INSERT_EIA_API_KEY_HERE")
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "INSERT_GUARDIAN_API_KEY_HERE")

# Gemini API key for Phase 1 risk extraction — get yours at https://aistudio.google.com/
# This is the APPLICATION's runtime key — NOT an agent/coding credit.
# Set GEMINI_API_KEY in your .env file (never hardcode here).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")   # empty → agent raises config error on startup
GEMINI_EXTRACTION_MODEL = "gemini-3.5-flash"        # Flash tier: cheap, fast, structured output

# These sources require no API key
# OFAC: public Treasury CDN
# GDELT: public DOC API
# RSS:   public feeds

# ── Source tiers ──────────────────────────────────────────────────────────────
# Tier 1 — Official / ground truth
TIER_1_SOURCES = ["EIA", "OFAC", "US_EIA_MONTHLY", "IEA"]

# Tier 2 — Structured event databases (corroborated signal)
TIER_2_SOURCES = ["GDELT", "GLOBAL_ENERGY_MONITOR"]

# Tier 3 — News text (supporting context only, never sole claim)
TIER_3_SOURCES = ["GUARDIAN", "RSS_TRADEWINDS", "RSS_LLOYDS", "RSS_PLATTS"]

# ── GDELT ─────────────────────────────────────────────────────────────────────
GDELT_DOC_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# ── EIA ───────────────────────────────────────────────────────────────────────
EIA_API_BASE = "https://api.eia.gov/v2"

# ── Guardian ──────────────────────────────────────────────────────────────────
GUARDIAN_API_BASE = "https://content.guardianapis.com"

# ── OFAC ──────────────────────────────────────────────────────────────────────
OFAC_SDN_XML_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
OFAC_SDN_ADVANCED_XML_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML"
OFAC_CONSOLIDATED_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML"

# ── RSS Feeds ─────────────────────────────────────────────────────────────────
RSS_FEEDS = {
    "tradewinds": "https://www.tradewindsnews.com/rss",
    "platts_energy": "https://www.spglobal.com/commodityinsights/en/rss-feed/oil",
    "eia_release": "https://www.eia.gov/rss/todayinenergy.xml",
    "reuters_energy": "https://feeds.reuters.com/reuters/businessNews",
}
# Primary feed to use for Phase 0 exit criteria
PRIMARY_RSS_FEED = "eia_release"

# ── Confidence score parameters ───────────────────────────────────────────────
CONFIDENCE_BASE = 0.3
CONFIDENCE_PER_CORROBORATING_SOURCE = 0.2
CONFIDENCE_MAX_CORROBORATING = 3
RECENCY_DECAY_HOURS = 72          # decay window in hours
RECENCY_MAX_MULTIPLIER = 1.0
RECENCY_MIN_MULTIPLIER = 0.5

# ── Synthetic AIS config ──────────────────────────────────────────────────────
# SYNTHETIC DATA — NOT LIVE AIS. See data_sources/ais_synthetic.py.
SYNTHETIC_AIS_NUM_VESSELS = 30
SYNTHETIC_AIS_OUTPUT_PATH = DATA_DIR / "synthetic_ais.json"

# ── Seeded reference vocabulary ───────────────────────────────────────────────
# The LLM extraction agent (Phase 1) must ONLY tag entities from these lists.
# Never generate free-text entity names — always match to this fixed vocabulary.

CORRIDORS = [
    "Strait of Hormuz",
    "Bab-el-Mandeb / Red Sea corridor",
    "Strait of Malacca",
]

REFINERIES = [
    "Jamnagar Refinery (Reliance)",
    "Panipat Refinery (IOC)",
    "Mumbai Refinery (BPCL)",
]

ALTERNATIVE_SUPPLIERS = [
    "Russian Urals Crude (via alternative routing)",
    "West African Crude (Nigeria/Angola)",
    "US WTI Export (via Cape of Good Hope routing)",
]

INDUSTRIES = [
    "Power generation",
    "Petrochemicals",
    "Transportation fuel / aviation",
    "Domestic LPG distribution",
]

# ── Historical crisis window ───────────────────────────────────────────────────
# The 2026 US-Iran / Strait of Hormuz crisis — ongoing as of July 20, 2026.
# Archive phases for Phase 5 backtesting:
CRISIS_PHASES = {
    "eruption":   ("2026-02-01", "2026-03-15"),   # Hostilities erupt, Brent ~$110, ~8M bbl/day disrupted
    "escalation": ("2026-03-16", "2026-06-30"),   # Sustained disruption, tanker "dark" crossings
    "blockade":   ("2026-07-01", "2026-07-19"),   # US reinstates blockade Jul 14, 20% cargo fee, Brent +9.5%
    "ongoing":    ("2026-07-14", "2026-07-20"),   # Still active — US-Iran still trading attacks
}
