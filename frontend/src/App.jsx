import { useState, useEffect } from 'react'

// Phase 0 — Placeholder landing page.
// Full UI components (map, event feed, approval workflow, graph explorer)
// will be built in Phase 4 once the backend pipeline is validated.

const CORRIDORS = [
  { name: 'Strait of Hormuz', status: 'CRITICAL', pct: 45 },
  { name: 'Bab-el-Mandeb / Red Sea', status: 'HIGH', pct: 18 },
  { name: 'Strait of Malacca', status: 'ELEVATED', pct: 22 },
]

const STATUS_COLORS = {
  CRITICAL: '#ef4444',
  HIGH:     '#f59e0b',
  ELEVATED: '#3b82f6',
  NORMAL:   '#22c55e',
}

const STATUS_BG = {
  CRITICAL: 'rgba(239,68,68,0.1)',
  HIGH:     'rgba(245,158,11,0.1)',
  ELEVATED: 'rgba(59,130,246,0.1)',
  NORMAL:   'rgba(34,197,94,0.1)',
}

export default function App() {
  const [tick, setTick] = useState(0)

  // Heartbeat animation tick
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 3000)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={styles.shell}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.logoGroup}>
            <div style={styles.logoMark}>⬡</div>
            <span style={styles.logoText}>RESILION</span>
            <span style={styles.logoTag}>Energy Intelligence</span>
          </div>
          <div style={styles.headerRight}>
            <div style={styles.phasePill}>Phase 0 — Foundation</div>
            <div style={{...styles.statusDot, background: tick % 2 === 0 ? '#22c55e' : '#16a34a'}}>
              <span style={styles.statusDotLabel}>LIVE</span>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main style={styles.main}>
        <section style={styles.hero}>
          <div style={styles.heroEyebrow}>AI-Driven Supply Chain Resilience</div>
          <h1 style={styles.heroTitle}>
            Energy Risk Intelligence<br />
            <span style={styles.heroAccent}>for Import-Dependent Economies</span>
          </h1>
          <p style={styles.heroSubtitle}>
            Two coordinated AI agents — the <strong>Risk Watcher</strong> and the{' '}
            <strong>Procurement Orchestrator</strong> — continuously monitor geopolitical
            signals and recommend supply chain responses. A human approves every action.
          </p>

          {/* Crisis banner */}
          <div style={styles.crisisBanner}>
            <div style={styles.crisisBannerDot} />
            <span style={styles.crisisBannerText}>
              <strong>ACTIVE CRISIS:</strong> 2026 US-Iran / Strait of Hormuz blockade — 
              Brent crude above $83 · US 20% cargo fee · ~8M bbl/day disrupted
            </span>
          </div>
        </section>

        {/* Corridor risk grid */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Monitored Corridors</h2>
          <div style={styles.corridorGrid}>
            {CORRIDORS.map(c => (
              <div key={c.name} style={{
                ...styles.corridorCard,
                borderColor: STATUS_COLORS[c.status],
                background: STATUS_BG[c.status],
              }}>
                <div style={styles.corridorHeader}>
                  <span style={styles.corridorName}>{c.name}</span>
                  <span style={{
                    ...styles.statusBadge,
                    color: STATUS_COLORS[c.status],
                    borderColor: STATUS_COLORS[c.status],
                    background: STATUS_BG[c.status],
                  }}>
                    {c.status}
                  </span>
                </div>
                <div style={styles.corridorStat}>
                  <span style={styles.corridorStatLabel}>India crude via this route</span>
                  <span style={{...styles.corridorStatValue, color: STATUS_COLORS[c.status]}}>
                    ~{c.pct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Phase status */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Build Progress</h2>
          <div style={styles.phaseGrid}>
            {[
              { n: 0, label: 'Foundation', status: 'IN PROGRESS', color: '#3b82f6' },
              { n: 1, label: 'Risk Intelligence Agent', status: 'PENDING', color: '#475569' },
              { n: 2, label: 'Graph Traversal & Scoring', status: 'PENDING', color: '#475569' },
              { n: 3, label: 'Procurement Orchestrator', status: 'PENDING', color: '#475569' },
              { n: 4, label: 'Human-in-the-Loop', status: 'PENDING', color: '#475569' },
              { n: 5, label: 'Historical Validation', status: 'PENDING', color: '#475569' },
            ].map(p => (
              <div key={p.n} style={{
                ...styles.phaseCard,
                borderColor: p.status === 'IN PROGRESS' ? p.color : 'transparent',
                opacity: p.status === 'PENDING' ? 0.5 : 1,
              }}>
                <span style={{...styles.phaseNum, color: p.color}}>Phase {p.n}</span>
                <span style={styles.phaseLabel}>{p.label}</span>
                <span style={{...styles.phaseBadge, color: p.color}}>{p.status}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Synthetic AIS disclosure */}
        <div style={styles.disclosure}>
          <span style={styles.disclosureIcon}>⚠</span>
          <span>
            Tanker position data shown in future UI views is{' '}
            <strong>SYNTHETIC</strong> — generated for demonstration purposes only.
            It is not connected to any live AIS (Automatic Identification System).
            Real AIS integration is a post-hackathon roadmap item.
          </span>
        </div>
      </main>
    </div>
  )
}

// ── Inline styles (Phase 0 — no component library yet) ──────────────────────

const styles = {
  shell: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0a0e1a 0%, #0d1528 50%, #0a0e1a 100%)',
    fontFamily: "'Inter', sans-serif",
  },
  header: {
    borderBottom: '1px solid #1e2d45',
    padding: '0 2rem',
    backdropFilter: 'blur(10px)',
    background: 'rgba(10,14,26,0.8)',
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  headerInner: {
    maxWidth: 1200,
    margin: '0 auto',
    height: 64,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logoGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  logoMark: {
    fontSize: '1.5rem',
    color: '#3b82f6',
    lineHeight: 1,
  },
  logoText: {
    fontSize: '1.1rem',
    fontWeight: 700,
    letterSpacing: '0.15em',
    color: '#e2e8f0',
  },
  logoTag: {
    fontSize: '0.7rem',
    color: '#475569',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginLeft: '0.25rem',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  phasePill: {
    fontSize: '0.72rem',
    padding: '0.25rem 0.75rem',
    borderRadius: 20,
    border: '1px solid #1d4ed8',
    color: '#60a5fa',
    letterSpacing: '0.05em',
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.5s ease',
    position: 'relative',
  },
  statusDotLabel: {
    position: 'absolute',
    right: 16,
    fontSize: '0.65rem',
    color: '#22c55e',
    letterSpacing: '0.08em',
  },
  main: {
    maxWidth: 1200,
    margin: '0 auto',
    padding: '4rem 2rem',
  },
  hero: {
    marginBottom: '4rem',
  },
  heroEyebrow: {
    fontSize: '0.8rem',
    letterSpacing: '0.15em',
    textTransform: 'uppercase',
    color: '#3b82f6',
    marginBottom: '1rem',
  },
  heroTitle: {
    fontSize: 'clamp(2rem, 5vw, 3.5rem)',
    fontWeight: 700,
    lineHeight: 1.15,
    color: '#e2e8f0',
    marginBottom: '1.5rem',
  },
  heroAccent: {
    background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  heroSubtitle: {
    fontSize: '1.1rem',
    color: '#94a3b8',
    maxWidth: 680,
    lineHeight: 1.7,
    marginBottom: '2rem',
  },
  crisisBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.875rem 1.25rem',
    borderRadius: 8,
    border: '1px solid rgba(239,68,68,0.3)',
    background: 'rgba(239,68,68,0.05)',
    maxWidth: 720,
  },
  crisisBannerDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#ef4444',
    flexShrink: 0,
    boxShadow: '0 0 8px #ef4444',
  },
  crisisBannerText: {
    fontSize: '0.875rem',
    color: '#fca5a5',
  },
  section: {
    marginBottom: '3rem',
  },
  sectionTitle: {
    fontSize: '0.75rem',
    fontWeight: 600,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: '#475569',
    marginBottom: '1.25rem',
    paddingBottom: '0.5rem',
    borderBottom: '1px solid #1e2d45',
  },
  corridorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '1rem',
  },
  corridorCard: {
    padding: '1.25rem',
    borderRadius: 10,
    border: '1px solid',
    backdropFilter: 'blur(4px)',
  },
  corridorHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  corridorName: {
    fontSize: '0.9rem',
    fontWeight: 600,
    color: '#e2e8f0',
  },
  statusBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    letterSpacing: '0.1em',
    padding: '0.2rem 0.5rem',
    borderRadius: 4,
    border: '1px solid',
  },
  corridorStat: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  corridorStatLabel: {
    fontSize: '0.8rem',
    color: '#64748b',
  },
  corridorStatValue: {
    fontSize: '1.5rem',
    fontWeight: 700,
    fontFamily: "'JetBrains Mono', monospace",
  },
  phaseGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '0.75rem',
  },
  phaseCard: {
    padding: '1rem',
    borderRadius: 8,
    background: 'rgba(17,24,39,0.8)',
    border: '1px solid',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
  },
  phaseNum: {
    fontSize: '0.7rem',
    fontWeight: 700,
    letterSpacing: '0.1em',
    fontFamily: "'JetBrains Mono', monospace",
  },
  phaseLabel: {
    fontSize: '0.875rem',
    color: '#e2e8f0',
    fontWeight: 500,
  },
  phaseBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    letterSpacing: '0.1em',
    marginTop: '0.25rem',
  },
  disclosure: {
    display: 'flex',
    gap: '0.75rem',
    padding: '0.875rem 1.25rem',
    borderRadius: 8,
    background: 'rgba(245,158,11,0.05)',
    border: '1px solid rgba(245,158,11,0.2)',
    fontSize: '0.8rem',
    color: '#fcd34d',
    lineHeight: 1.6,
    marginTop: '2rem',
  },
  disclosureIcon: {
    fontSize: '1rem',
    flexShrink: 0,
  },
}
