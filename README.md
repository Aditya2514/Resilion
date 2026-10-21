<div align="center">

![Resilion Hero Banner](docs/assets/hero_banner.png)

# ⬡ RESILION
### *AI-Driven Energy Supply Chain Resilience & Geo-Risk Intelligence*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![NetworkX](https://img.shields.io/badge/Knowledge_Graph-NetworkX_3.3-FF6F00?style=for-the-badge)](https://networkx.org)
[![Gemini AI](https://img.shields.io/badge/AI_Engine-Gemini_2.5_Flash-8E44AD?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<p align="center">
  <a href="#-status-what-works-today">Status</a> •
  <a href="#-executive-summary">Executive Summary</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-key-features">Key Features</a> •
  <a href="#-ai-agents">AI Agents</a> •
  <a href="#-user-interface">UI</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-project-roadmap--phase-status">Roadmap</a>
</p>

</div>

---

## ✅ Status: what works today

Resilion is an in-progress hackathon project. The foundation and the first agent are built; the second agent, the API and the approval console are not.

| Component | State | Where |
|:---|:---:|:---|
| Seeded NetworkX knowledge graph (13 nodes, 19 edges), JSON save/reload | ✅ Built | `backend/graph/seed.py`, `backend/graph/store.py` |
| Data connectors: GDELT, EIA, OFAC SDN, Guardian, RSS (+ synthetic AIS generator) | ✅ Built (standalone fetchers) | `backend/data_sources/` |
| Risk Watcher agent: Gemini 2.5 Flash extraction → validated Event/Source nodes in the graph | ✅ Built (run via validation script) | `backend/agents/risk_agent.py` |
| Phase 0 exit-criteria script (8 steps) | ✅ Passes (uses a local mock event if GDELT, RSS and OFAC are all unreachable) | `backend/scripts/exit_criteria.py` |
| Corridor → refinery → industry walk (`find_affected_industries`) | ✅ Basic 2-hop walk | `backend/graph/traversal.py` |
| Disruption scoring, recommendation explanation paths | 📅 Planned (stubs return `0.0` / `[]`) | `backend/graph/traversal.py` |
| Procurement Orchestrator agent (second agent) | 📅 Planned | — |
| FastAPI backend / human-in-the-loop approval endpoints | 📅 Planned (Phase 4) | `backend/api/__init__.py` is a placeholder |
| React dashboard | 🟡 Static placeholder landing page | `frontend/src/App.jsx` |
| Historical backtesting against the 2026 Hormuz crisis | 📅 Planned (archive builder exists) | `backend/historical/build_archive.py` |

---

## 🌍 Executive Summary

Import-dependent economies face existential risks during sudden geopolitical maritime blockades. **India imports ~88% of its crude oil**, with **40-45% transiting the Strait of Hormuz** — a strategic bottleneck subject to military blockades and severe supply shocks (e.g. the 2026 US-Iran crisis driving Brent crude near \$110/bbl with ~8M bbl/day unavailable).

Traditional supply chain tools rely on static ERP lookups and lack real-time signal processing. Raw LLM assistants, on the other hand, can produce unverifiable free-text answers with no traceable reasoning.

**Resilion's design** is **two coordinated AI agents** operating over a deterministic **NetworkX knowledge graph**:

1. **Risk Watcher Agent** *(built)*: Takes news text (today: GDELT headlines and Guardian article text from the historical crisis archive), extracts structured disruption events with Gemini, scores their confidence, and inserts them into the knowledge graph. EIA and OFAC records are fetched by the connectors but not yet fed to the agent.
2. **Procurement Orchestrator Agent** *(planned, Phase 3)*: Will trigger on disruption signals, compute cascading supply impacts across refineries and downstream industries, rank alternative crude sources, and produce graph-traced recommendations.

> **🛡️ Human-in-the-Loop by design (planned, Phase 4):** The intended system never auto-executes procurement or rerouting actions; every recommendation would require explicit human approval in a control console. The approval console and its API are not implemented yet.

---

## 🏗️ System Architecture

The target architecture has four layers. Layers 1 and 3 and the Risk Watcher are implemented; the rest is the roadmap.

```
┌─────────────────────────────────────────────────────────────────────────┐
│              LAYER 1: MULTI-TIER DATA INGESTION  [built]                │
│  Tier 1 (Ground Truth): EIA Open Data, OFAC Sanctions List              │
│  Tier 2 (Corroborated Signal): GDELT DOC API                            │
│  Tier 3 (Supporting Context): Guardian API, Energy/Maritime RSS         │
│  + Synthetic AIS tanker generator (clearly labelled SYNTHETIC)          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Headlines / article text (GDELT / Guardian archive)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LAYER 2: AI AGENTS                                  │
│  ┌──────────────────────────────┐     ┌──────────────────────────────┐  │
│  │  RISK WATCHER AGENT [built]  │     │ PROCUREMENT ORCHESTRATOR     │  │
│  │ • Keyword pre-filter         │     │          [planned]           │  │
│  │ • Gemini structured extract  │ ──► │ • Graph impact traversal     │  │
│  │ • Vocabulary validation      │     │ • Route cost & ETA ranking   │  │
│  │ • Confidence score           │     │ • Graph-traced rationale     │  │
│  └──────────────────────────────┘     └──────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Graph mutations & queries
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             LAYER 3: NETWORKX KNOWLEDGE GRAPH CORE  [built]             │
│   Seeded: Corridors (3) | Refineries (3) | Suppliers (3) | Industries (4) │
│   Edges in use: SUPPLIES, SERVES, REPORTED_BY, OCCURRED_IN              │
│   Defined, not yet wired: CO_OCCURS_WITH, TARGETS, TRANSITS, DIVERTS_TO │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│         LAYER 4: FASTAPI BACKEND & HUMAN-IN-THE-LOOP UI  [planned]      │
│  • REST API for events, traversals and approvals (not implemented)      │
│  • React command center & decision console (placeholder page today)     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Key Features

- **📡 Source tiers** (`backend/config.py`): every Source/Event node records the tier of the source that reported it.
  - **Tier 1** — official data (`EIA`, `OFAC`), treated as ground truth.
  - **Tier 2** — structured event databases (`GDELT`).
  - **Tier 3** — news text (`Guardian`, `RSS`), supporting context only.
  - The tier is stored on nodes and edges as audit metadata; it does not yet weight the confidence score.
- **🧮 Confidence formula** (`compute_confidence` in `backend/agents/risk_agent.py`):
  $$\text{Confidence} = \big(0.3 + 0.2 \times \min(\text{Corroborating}, 3)\big) \times \text{RecencyMultiplier}$$
  The recency multiplier decays linearly from 1.0 to 0.5 over 72 hours, measured against the current clock (0.75 if the event date is unknown), so archive articles older than 72 hours get 0.5. "Corroborating" currently counts existing events in the graph with the same corridor and event type within ±4 hours, a stated proxy until event deduplication lands in Phase 2. A fresh, uncorroborated event scores 0.30; a fully corroborated fresh event scores 0.90.
- **🔒 Constrained LLM output**: Gemini is called with a Pydantic response schema at temperature 0. Corridor, event type and severity must come from a fixed seeded vocabulary; the extracted output is re-validated with Pydantic, and a corridor name that does not match the seeded list is set to null rather than inserted as a new corridor. Articles are keyword pre-filtered before any LLM call, and the model's own relevance flag is a second filter.
- **🕸️ Structural explainability (design goal)**: recommendations are meant to be justified by walking real graph edges rather than free-text LLM output. Today the graph stores the audit trail (`REPORTED_BY` edges with confidence and source tier, `OCCURRED_IN` edges with confidence); the backward explanation walk (`explain_recommendation`) is a Phase 3 stub.
- **🚨 Seeded strategic corridors** (`backend/graph/seed.py`; the risk levels and India-share figures are static reference values, not computed):
  - **Strait of Hormuz** (~40-45% of India's crude — seeded as *CRITICAL*)
  - **Bab-el-Mandeb / Red Sea** (seeded as *HIGH*)
  - **Strait of Malacca** (seeded as *ELEVATED*)

---

## 🤖 AI Agents

### 1. Risk Watcher Agent (`backend/agents/risk_agent.py`) — built
`RiskAgent.extract_and_insert()` takes one article (text + metadata) and runs: keyword pre-filter → `gemini-2.5-flash` structured extraction → vocabulary normalisation → confidence scoring → Event + Source node insertion with `REPORTED_BY` and `OCCURRED_IN` edges. It is run in batch over a historical article archive by `scripts/run_phase1_validation.py`; there is no continuous ingestion loop yet.

Shape of an inserted Event node (illustrative values, subset of fields from `EventNode` in `backend/graph/schema.py`):

```json
{
  "node_id": "event:guardian:3f2a9c1b7d4e",
  "event_type": "BLOCKADE",
  "corridor": "Strait of Hormuz",
  "region": "Persian Gulf",
  "severity": "CRITICAL",
  "confidence": 0.3,
  "corroborating_sources": 0,
  "source_tier": 3,
  "extraction_model": "gemini-2.5-flash"
}
```

### 2. Procurement Orchestrator Agent — planned (Phase 3)
Not implemented. What exists today in `backend/graph/traversal.py` is `find_affected_industries()`, a two-hop walk from a corridor through `SUPPLIES` edges to refineries (**Jamnagar**, **Panipat**, **Mumbai**) and through `SERVES` edges to industries (**Power generation**, **Petrochemicals**, **Transportation fuel / aviation**, **Domestic LPG distribution**). For the Strait of Hormuz it returns 10 refinery→industry paths. Its `disruption_score` field is `None` until Phase 2.

The graph is also seeded with three alternative suppliers that the Orchestrator is designed to rank — **West African crude (Nigeria/Angola)**, **US WTI export** and **Russian Urals** — each with grade, API gravity, sulfur content and typical route. Cost (\$/bbl) and transit-delay (ETA) estimates and the ranking itself are not computed yet.

---

## 🖥️ User Interface

**What exists today:** `frontend/` is a Vite + React placeholder landing page (`frontend/src/App.jsx`) with a project description, three static corridor cards and a build-progress grid. It does not call the backend.

**Planned UI (concept mockups, not screenshots):** the images below are AI-generated design mockups of the Phase 4 console. They are not screenshots of running code, and the numbers shown in them (percentages, confidence values, +days ETA, +\$/bbl) are illustrative, not computed by Resilion.

### 1. Threat Command Center & Corridor Risk Grid (concept)
![Resilion dashboard concept mockup](docs/assets/dashboard_ui.png)
*Concept: corridor threat gauges, crisis ticker and a tiered intelligence feed.*

### 2. Knowledge Graph Explorer & HITL Approval Console (concept)
![Resilion orchestrator concept mockup](docs/assets/orchestrator_ui.png)
*Concept: disruption paths (red) versus rerouting options (green), recommendation cards and a human approval button. None of this is implemented yet.*

---

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: v18.0 or higher (frontend only)
- **npm**: v9.0 or higher

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/Aditya2514/Resilion.git
cd Resilion/backend

# Create & activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

> **API keys**: `backend/config.py` reads a `.env` file in the **repository root** (there is no `.env.example`; create the file yourself). GDELT, OFAC and RSS need no key. Set `EIA_API_KEY` and `GUARDIAN_API_KEY` for those feeds (`python scripts/check_keys.py` tests them), and `GEMINI_API_KEY` for the Risk Watcher agent.

### 2. Verify Phase 0 Exit Criteria

```bash
python scripts/exit_criteria.py
```

The script seeds the graph (13 nodes, 19 edges), pulls one live item (GDELT, then EIA RSS, then OFAC; if all of them are unreachable it falls back to a local mock event and says so), builds and inserts Event + Source nodes (15 nodes, 21 edges), runs the Hormuz traversal (10 industry paths), saves the graph to JSON and reloads it to check integrity. Its summary prints:

```text
  Steps passed: 8/8

  ✓  All 8 steps passed cleanly.

  [PHASE 0 EXIT CRITERIA: PASSED]
```

### 3. Run the Risk Watcher (Phase 1)

```bash
# Build the 2026 Hormuz-crisis article archive from GDELT (+ Guardian if keyed)
python historical/build_archive.py

# Extract events from up to 10 risk-relevant articles with Gemini and check vocabulary containment
python scripts/run_phase1_validation.py
```

Requires `GEMINI_API_KEY`. No run results are committed to the repo.

### 4. Frontend (placeholder page)

```bash
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173` to see the placeholder landing page.

---

## 🗺️ Project Roadmap & Phase Status

| Phase | Milestone | Status | Description |
|:---:|:---|:---:|:---|
| **Phase 0** | **Foundation & Graph Plumbing** | ✅ **PASSED** | Seeded NetworkX graph, live-source fallbacks, JSON state persistence; `exit_criteria.py` passes |
| **Phase 1** | **Risk Intelligence Agent** | 🔄 **IN PROGRESS** | Gemini 2.5 Flash extraction pipeline and validation script built; no committed validation results yet |
| **Phase 2** | **Graph Traversal & Scoring** | 📅 **PLANNED** | Corridor disruption scores, multi-hop propagation, event deduplication (`CO_OCCURS_WITH`) for true corroboration |
| **Phase 3** | **Procurement Orchestrator** | 📅 **PLANNED** | Second agent: alternative-supplier cost/ETA ranking, graph-traced recommendation rationale |
| **Phase 4** | **Human-in-the-Loop Console** | 📅 **PLANNED** | FastAPI approval endpoints, full React dashboard |
| **Phase 5** | **Historical Crisis Backtesting**| 📅 **PLANNED** | Validation against the Feb–Jul 2026 Strait of Hormuz article archive |
| **Phase 6** | **Stretch Features** | 📅 **PLANNED** | Natural-language graph querying, live AIS vessel integration, OFAC `TARGETS` edges |

---

## ⚠️ Disclosures & Ethics

- **Synthetic AIS Data**: `backend/data_sources/ais_synthetic.py` generates **SYNTHETIC** tanker positions for demos. It is not connected to a live AIS receiver and is not yet wired into the graph.
- **Concept imagery**: the banner and UI mockups in `docs/assets/` are AI-generated illustrations, not screenshots.
- **No Financial Auto-Execution**: Resilion is designed as decision support only. All procurement orders, credit allocations and ship charters are meant to require human sign-off.

---

<div align="center">

**Resilion Energy Intelligence** • Built for Hackathon 2026

</div>
