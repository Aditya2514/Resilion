# Resilion — AI-Driven Energy Supply Chain Resilience

> **Hackathon project** — AI-powered risk intelligence for import-dependent economies facing geopolitical supply shocks.

## The problem

India sources ~88% of its crude oil from imports, with 40-45% transiting the Strait of Hormuz — a corridor being actively disrupted by the **ongoing 2026 US-Iran crisis** (Brent near $110/bbl peak, US 20% cargo fee blockade reinstated July 14, 2026, ~8M bbl/day unavailable).

## The system

Two coordinated AI agents sharing a NetworkX knowledge graph:

| Agent | Role |
|---|---|
| **Risk Watcher** | Reads news/data sources → extracts structured events → writes to graph |
| **Procurement Orchestrator** | On disruption alert → ranks alternative crude sources/routes → generates graph-traced recommendations |

**Human-in-the-loop always** — no agent output auto-executes. All recommendations require human approval.

## Architecture

```
data_sources/     → EIA (T1), OFAC (T1), GDELT (T2), Guardian (T3), RSS (T3)
graph/            → NetworkX DiGraph, schema, seeding, traversal
agents/           → Risk Watcher (Phase 1), Orchestrator (Phase 3)
api/              → FastAPI approval workflow (Phase 4)
historical/       → Feb-Jul 2026 crisis archive for Phase 5 backtesting
frontend/         → React dashboard (Phase 4)
```

## Source tiers

| Tier | Sources | Trust |
|---|---|---|
| **T1** | EIA, OFAC | Ground truth |
| **T2** | GDELT | Corroborated signal |
| **T3** | Guardian, RSS | Supporting context |

Never present a T3-only claim with the same confidence as a T1 fact.

## Setup

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Set API keys (optional for Phase 0 — GDELT and OFAC work without keys)
copy .env.example .env
# Edit .env with your EIA and Guardian API keys
```

### Run Phase 0 exit criteria
```bash
cd backend
python scripts/exit_criteria.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment variables
```
EIA_API_KEY=your_key_here      # https://www.eia.gov/opendata/register.php
GUARDIAN_API_KEY=your_key_here # https://open-platform.theguardian.com/access/
```

## Phase roadmap

| Phase | Status | Description |
|---|---|---|
| 0 — Foundation | ✅ Done | Data plumbing, seeded graph, exit criteria |
| 1 — Risk Intelligence Agent | ⬜ Next | LLM extraction pipeline |
| 2 — Graph Traversal & Scoring | ⬜ | Disruption propagation, confidence scores |
| 3 — Procurement Orchestrator | ⬜ | Alternative route ranking |
| 4 — Human-in-the-Loop | ⬜ | Approval workflow, audit trail |
| 5 — Historical Validation | ⬜ | 2026 crisis backtest |
| 6+ — Polish & Stretch | ⬜ | NL query, scenario presets, map |

## Key design principles

- **Human-in-the-loop always** — no auto-execution
- **Explainability is structural** — rationale comes from graph edge traversal, never free-text LLM
- **Source-tier honesty** — confidence formula: `0.3 + 0.2 × min(corroborating_sources, 3) + recency_multiplier`
- **Disclose synthetic data** — AIS tanker positions are clearly labeled `SYNTHETIC`
- **Scope discipline** — 2 agents, done well; no scope creep

## Seeded corridors

| Corridor | India crude % | 2026 risk |
|---|---|---|
| Strait of Hormuz | ~45% | CRITICAL — active blockade |
| Bab-el-Mandeb / Red Sea | ~18% | HIGH |
| Strait of Malacca | ~22% | ELEVATED |
