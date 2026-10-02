import { useState } from 'react'
import { Link } from 'react-router-dom'
import './Landing.css'

const PROBLEMS = [
  { icon:'👁️', color:'blue',  title:'Visibility Gap', desc:'Bill sirf ek total number — kaun si machine kitni bijli kha rahi hai, yeh pata nahi.' },
  { icon:'🔍', color:'amber', title:'Diagnosis Gap',   desc:'Bill kyun badha? Machine kharab hai, shift kharab hai, ya power factor gira — koi baat nahi batata.' },
  { icon:'⚙️', color:'green', title:'Action Gap',      desc:'Off-peak tariff ka fayda kaise loon? Koi tool nahi. Plant manager guess karta hai.' },
  { icon:'📋', color:'red',   title:'Proof Gap',       desc:'Export buyer carbon data maang raha hai — GHG Protocol report SME ke paas hai hi nahi.' },
]

const LAYERS = [
  { n:1, icon:'📥', label:'Data Ingestion',     sub:'Bill PDF/CSV upload — bill parsing in Phase 2' },
  { n:2, icon:'🏗️', label:'Digital Twin',       sub:'Physics simulation (Phase 1). SimPy planned Phase 2' },
  { n:3, icon:'🧠', label:'NILM Disaggregation',sub:'Physics sim Phase 1. Seq2Point/IMDELD in Phase 2' },
  { n:4, icon:'🔴', label:'Anomaly Detection',  sub:'Physics rules Phase 1. LSTM-VAE in Phase 2' },
  { n:5, icon:'📅', label:'Tariff Scheduler',   sub:'CP-SAT (real, OR-Tools). PPO RL is Phase 2' },
  { n:6, icon:'🌿', label:'Carbon + Copilot',   sub:'GHG Scope 1+2, rule-based copilot. LLM in Phase 2' },
]

const STATS = [
  { val:'17.6%',    label:'Scheduler saving (CP-SAT verified)', color:'blue'  },
  { val:'Rs.40K+',  label:'Tariff saving/month (26 working days)', color:'amber' },
  { val:'34.5 tCO2',label:'Sep 2026 Scope 2 emissions tracked', color:'green' },
  { val:'Rs.0',     label:'Hardware cost (software-only)',        color:'purple'},
]

const INDUSTRIES = ['🔩 Foundry','🧵 Textile','🏺 Ceramics','🧱 Brick Kiln','🧪 Chemical','🍞 Food Processing']

export default function Landing() {
  const [activeLayer, setActiveLayer] = useState(null)

  return (
    <div className="landing-page">
      {/* ── HERO ── */}
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-inner container">
          <div className="hero-badge">⚡ Zero Hardware · AI-Powered · Made for India</div>
          <h1 className="hero-title">
            India ke SMEs ke liye<br />
            <span className="gradient-text font-outfit">AI Energy Intelligence</span>
          </h1>
          <p className="hero-sub">
            Sirf bijli bill upload karo — UrjaMind bina kisi sensor ke batayega kaun si machine 
            kitni bijli kha rahi hai, kahan waste hai, aur carbon report bhi dega.
          </p>
          <div className="hero-ctas">
            <Link to="/upload" className="btn btn-primary" style={{fontSize:16,padding:'14px 32px'}}>
              🚀 Shuru Karo — Free
            </Link>
            <a href="#how-it-works" className="btn btn-secondary">Kaise kaam karta hai? ↓</a>
          </div>
          <div className="hero-stats">
            {STATS.map((s,i) => (
              <div key={i} className="hero-stat">
                <div className={`hero-stat-val gradient-text`} style={{color:`var(--${s.color})`}}>{s.val}</div>
                <div className="hero-stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Problems ── */}
      <section className="section" id="problems">
        <div className="container">
          <div className="section-label">THE PROBLEM</div>
          <h2 className="section-title">SME Plant Manager ke paas jawab nahi hote</h2>
          <p className="section-desc">India ke industry sector mein total energy ka 35–40% use hota hai, lekin plant manager ke paas yeh 4 sawaalon ka jawab nahi hota:</p>
          <div className="problems-grid">
            {PROBLEMS.map((p,i) => (
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
          <div className="section-label">THE SOLUTION</div>
          <h2 className="section-title">UrjaMind — 6-Layer AI Pipeline</h2>
          <p className="section-desc">Ek bill se shuru karo, machine-level intelligence tak pahuncho</p>
          <div className="pipeline">
            <div className="pipe-input">
              <div className="pipe-source">📄 Bijli Bill</div>
              <div className="pipe-source">📊 DISCOM CSV</div>
              <div className="pipe-source">💬 WhatsApp</div>
              <div className="pipe-source">🏭 Production Log</div>
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-layers">
              {LAYERS.map((l,i) => (
                <div
                  key={i}
                  className={`pipe-layer ${activeLayer===i?'pipe-layer-active':''}`}
                  onClick={() => setActiveLayer(activeLayer===i?null:i)}
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
              <div className="pipe-out green">🌿 Carbon Report</div>
              <div className="pipe-out purple">🤖 Copilot Chat</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Data Tiers ── */}
      <section className="section">
        <div className="container">
          <div className="section-label">DATA-TIER DESIGN</div>
          <h2 className="section-title">Jitna data — utna accuracy</h2>
          <p className="section-desc">Har SME ke paas alag quality ka data hota hai — UrjaMind gracefully adapt karta hai</p>
          <div className="tiers-grid">
            {[
              {tier:'Tier 1',data:'Monthly Bill Only',outputs:['Baseline kWh/unit','PF & MD analysis','Bill benchmark'],conf:'Low–Medium'},
              {tier:'Tier 2',data:'DISCOM 15/30-min Interval',outputs:['Machine disaggregation (NILM)','Shift-wise analysis','Anomaly detection'],conf:'High',highlight:true},
              {tier:'Tier 3',data:'High-res + Production Log',outputs:['Machine-level precision','Predictive maintenance','Full M&V verification'],conf:'Very High'},
            ].map((t,i) => (
              <div key={i} className={`tier-card ${t.highlight?'tier-highlight':''}`}>
                <div className="tier-tag">{t.tier}</div>
                <div className="tier-data">{t.data}</div>
                <ul className="tier-list">
                  {t.outputs.map((o,j) => <li key={j}>{o}</li>)}
                </ul>
                <div className={`badge ${i===0?'badge-amber':i===1?'badge-green':'badge-blue'}`}>Confidence: {t.conf}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Industries ── */}
      <section className="section section-dark">
        <div className="container" style={{textAlign:'center'}}>
          <div className="section-label">TARGET SECTORS</div>
          <h2 className="section-title">Kis tarah ke plants ke liye hai?</h2>
          <div className="industries-wrap">
            {INDUSTRIES.map((ind,i) => <div key={i} className="industry-chip">{ind}</div>)}
          </div>
          <p className="section-desc" style={{marginTop:20}}>Rajkot foundries · Ludhiana hosiery · Morbi ceramics · Surat textile · aur bahut zyada...</p>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="section cta-section">
        <div className="container" style={{textAlign:'center'}}>
          <h2 className="section-title gradient-text">Abhi shuru karo — free mein</h2>
          <p className="section-desc" style={{marginBottom:32}}>Rajkot Foundry ka demo dekho ya apna data upload karo</p>
          <div style={{display:'flex',gap:16,justifyContent:'center',flexWrap:'wrap'}}>
            <Link to="/upload" className="btn btn-primary" style={{fontSize:16,padding:'14px 32px'}}>📥 Upload Your Data</Link>
            <Link to="/dashboard" className="btn btn-secondary" style={{fontSize:16}}>📊 Live Demo Dashboard</Link>
          </div>
        </div>
      </section>
    </div>
  )
}
