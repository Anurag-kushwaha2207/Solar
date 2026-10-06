import { useState } from 'react'
import { Link } from 'react-router-dom'
import './Landing.css'

const PROBLEMS = [
  {
    icon: '👁️',
    color: 'blue',
    title: 'Visibility Gap',
    desc: 'A monthly bill gives only a lump-sum kWh. Understanding which equipment consumes what portion usually requires expensive meters.'
  },
  {
    icon: '🔍',
    color: 'amber',
    title: 'Diagnosis Gap',
    desc: 'Did your bill rise due to power factor penalties, compressor leaks, off-peak slippage, or higher production volume?'
  },
  {
    icon: '⚙️',
    color: 'green',
    title: 'Action Gap',
    desc: 'Taking advantage of Time-of-Day (ToD) off-peak rebates requires rigorous mathematical shift scheduling, not guesswork.'
  },
  {
    icon: '📋',
    color: 'red',
    title: 'Compliance & Proof Gap',
    desc: 'Global supply chain buyers require auditable GHG Protocol Scope 1 & 2 carbon footprints that most SMEs cannot easily report.'
  },
]

const LAYERS = [
  { n: 1, icon: '📥', label: 'Data Ingestion', sub: 'Electricity bills, 15-min interval CSVs, production logs' },
  { n: 2, icon: '🏗️', label: 'Plant Modeling', sub: 'Physics priors and load parameter modeling' },
  { n: 3, icon: '🧠', label: 'Load Disaggregation', sub: 'Physics-informed machine-level energy estimates' },
  { n: 4, icon: '🔴', label: 'Anomaly Detection', sub: 'Power factor penalties, standby leaks, and demand spikes' },
  { n: 5, icon: '📅', label: 'Tariff Scheduler', sub: 'Google OR-Tools CP-SAT mathematical optimization' },
  { n: 6, icon: '🌿', label: 'Carbon & Copilot', sub: 'GHG Protocol Scope 1 & 2 accounting + AI assistant' },
]

const VALUE_PILLARS = [
  { val: 'ToD Aware', label: 'Off-peak tariff scheduling', color: 'blue' },
  { val: '₹0 CapEx', label: 'Hardware-free initial audit', color: 'green' },
  { val: 'GHG Protocol', label: 'Scope 1 & 2 carbon tracking', color: 'accent-lime' },
  { val: '3 Data Tiers', label: 'Adapts to data availability', color: 'purple' },
]

const INDUSTRIES = [
  '🔩 Foundries & Forging',
  '🧵 Textile & Apparel',
  '🏺 Ceramics & Tiles',
  '🧱 Plastics & Extrusion',
  '🧪 Chemical Processing',
  '🍞 Food & Agro Processing'
]

export default function Landing() {
  const [activeLayer, setActiveLayer] = useState(null)

  return (
    <div className="landing-page">
      {/* ── HERO ── */}
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-inner container">
          <div className="hero-badge">⚡ Zero Hardware Required · AI Energy Intelligence · Built for Indian Industry</div>
          <h1 className="hero-title">
            Intelligent Energy Management for<br />
            <span className="gradient-text font-outfit">Indian Manufacturing</span>
          </h1>
          <p className="hero-sub">
            Upload your electricity bill and a few plant details. UrjaMind estimates where energy is used,
            flags waste, and suggests tariff-aware schedules.
          </p>
          <div className="hero-ctas">
            <Link to="/upload" className="btn btn-primary" style={{ fontSize: 16, padding: '14px 32px' }}>
              🚀 Get Started — Free
            </Link>
            <a href="#how-it-works" className="btn btn-secondary">How it works ↓</a>
          </div>

          <div className="hero-stats">
            {VALUE_PILLARS.map((s, i) => (
              <div key={i} className="hero-stat">
                <div className="hero-stat-val gradient-text">{s.val}</div>
                <div className="hero-stat-label">{s.label}</div>
              </div>
            ))}
          </div>
          <div className="hero-note">
            ℹ️ Prototype — estimates based on physics simulation priors, DISCOM tariff structures, and uploaded plant logs.
          </div>
        </div>
      </section>

      {/* ── Problems ── */}
      <section className="section" id="problems">
        <div className="container">
          <div className="section-label">THE CHALLENGE</div>
          <h2 className="section-title">Critical questions factory managers face every month</h2>
          <p className="section-desc">
            Industrial electricity expenses represent a significant operating cost for SMEs, yet plants often lack the granular visibility needed to optimize.
          </p>
          <div className="problems-grid">
            {PROBLEMS.map((p, i) => (
              <div key={i} className={`problem-card problem-${p.color}`}>
                <div className="problem-icon">{p.icon}</div>
                <h3 className="problem-title">{p.title}</h3>
                <p className="problem-desc">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works / Pipeline ── */}
      <section className="section section-dark" id="how-it-works">
        <div className="container">
          <div className="section-label">HOW IT WORKS</div>
          <h2 className="section-title">UrjaMind 6-Layer Intelligence Pipeline</h2>
          <p className="section-desc">
            Progressive intelligence pipeline: starting from monthly utility bills up to detailed equipment logs.
          </p>
          <div className="pipeline">
            <div className="pipe-input">
              <div className="pipe-source">📄 Utility Bill</div>
              <div className="pipe-source">📊 Interval CSV</div>
              <div className="pipe-source">🏭 Production Log</div>
              <div className="pipe-source">⚙️ Equipment Register</div>
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-layers">
              {LAYERS.map((l, i) => (
                <div
                  key={i}
                  className={`pipe-layer ${activeLayer === i ? 'pipe-layer-active' : ''}`}
                  onClick={() => setActiveLayer(activeLayer === i ? null : i)}
                  role="button"
                  tabIndex={0}
                  aria-label={l.label}
                  onKeyDown={(e) => { if (e.key === 'Enter') setActiveLayer(activeLayer === i ? null : i) }}
                >
                  <span className="pipe-n">L{l.n}</span>
                  <span className="pipe-icon">{l.icon}</span>
                  <div>
                    <div className="pipe-label">{l.label}</div>
                    <div className="pipe-sub">{l.sub}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-outputs">
              <div className="pipe-out blue">📊 Energy Dashboard</div>
              <div className="pipe-out amber">📅 Shift Schedule</div>
              <div className="pipe-out green">🌿 Carbon Audit</div>
              <div className="pipe-out purple">🤖 Plant Copilot</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Data Tiers ── */}
      <section className="section">
        <div className="container">
          <div className="section-label">TIERED ACCURACY DESIGN</div>
          <h2 className="section-title">Transparent accuracy scaling with your data</h2>
          <p className="section-desc">
            Different facilities possess varying levels of digital logging. UrjaMind is engineered to provide actionable results at every level without claiming unverified precision.
          </p>
          <div className="tiers-grid">
            {[
              {
                tier: 'Tier 1',
                data: 'Monthly Utility Bill Only',
                outputs: [
                  'Baseline energy cost per unit output',
                  'Power factor and max demand penalty checks',
                  'DISCOM tariff compliance audit'
                ],
                conf: 'Initial Estimate',
              },
              {
                tier: 'Tier 2',
                data: 'DISCOM Interval Meter Data',
                outputs: [
                  '24-hour diurnal load curve profiling',
                  'Shift-wise consumption attribution',
                  'Time-of-Day (ToD) tariff optimization potential'
                ],
                conf: 'High',
                highlight: true
              },
              {
                tier: 'Tier 3',
                data: 'Interval Logs + Equipment Register',
                outputs: [
                  'Physics-guided machine load disaggregation',
                  'Constraint-satisfying CP-SAT shift scheduling',
                  'Auditable GHG Protocol Scope 1 & 2 carbon accounting'
                ],
                conf: 'Highest Precision'
              },
            ].map((t, i) => (
              <div key={i} className={`tier-card ${t.highlight ? 'tier-highlight' : ''}`}>
                <div className="tier-tag">{t.tier}</div>
                <div className="tier-data">{t.data}</div>
                <ul className="tier-list">
                  {t.outputs.map((o, j) => <li key={j}>• {o}</li>)}
                </ul>
                <div className={`badge ${i === 0 ? 'badge-amber' : i === 1 ? 'badge-green' : 'badge-blue'}`}>
                  Confidence: {t.conf}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Industries ── */}
      <section className="section section-dark">
        <div className="container" style={{ textAlign: 'center' }}>
          <div className="section-label">TARGET SECTORS</div>
          <h2 className="section-title">Designed for energy-intensive industrial clusters</h2>
          <div className="industries-wrap">
            {INDUSTRIES.map((ind, i) => <div key={i} className="industry-chip">{ind}</div>)}
          </div>
          <p className="section-desc" style={{ marginTop: 24, marginInline: 'auto' }}>
            Light engineering clusters · Foundries · Textile weaving & spinning · Plastic molding · Ceramic tiles · Food processing
          </p>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="section cta-section">
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="section-title gradient-text">Get started today — free</h2>
          <p className="section-desc" style={{ marginBottom: 32, marginInline: 'auto' }}>
            Upload your plant documentation or explore the interactive sample plant dashboard.
          </p>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/upload" className="btn btn-primary" style={{ fontSize: 16, padding: '14px 32px' }}>
              📥 Upload Your Plant Data
            </Link>
            <Link to="/dashboard" className="btn btn-secondary" style={{ fontSize: 16 }}>
              📊 Sample Plant Demo
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

