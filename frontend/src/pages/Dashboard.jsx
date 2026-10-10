import { useState, useEffect, useRef } from 'react'
import {
  BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import toast from 'react-hot-toast'
import { fetchKPIs, fetchMachines, fetchBaseline, fetchAnomalies, fetchNILM, chatWithCopilot, fetchQuickQs, resolveAnomaly } from '../api'
import { logCopilotChat, auth } from '../firebase'
import './Dashboard.css'

const COLORS = ['#22c55e', '#a3e635', '#2dd4bf', '#f5a800', '#94a3b8', '#38bdf8']
const SEV_COLOR = { high: 'var(--danger)', medium: 'var(--warn)', low: 'var(--primary)' }

// ── Synthetic 24h baseline load profile fallback ─────────────────────────────
function genLoadProfile() {
  const h = Array.from({ length: 24 }, (_, i) => i)
  return h.map(hr => ({
    hour: `${hr}:00`,
    Furnace: hr >= 6 && hr < 22 ? 120 + Math.random() * 40 : 6,
    Compressor: hr >= 6 && hr < 22 ? 38 + Math.random() * 18 : 4.2,
    Press: hr >= 6 && hr < 18 ? 55 + Math.random() * 20 : 1,
    Fettling: hr >= 6 && hr < 18 ? 30 + Math.random() * 14 : 0.5,
    Misc: 8 + Math.random() * 6,
  }))
}
const LOAD_DATA = genLoadProfile()

// ── KPI Card ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, unit, sub, delta, deltaType, icon, color, statusBadge = 'Measured' }) {
  return (
    <div className={`kpi-card kpi-${color}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div className="kpi-icon">{icon}</div>
        <span className={`badge-status badge-${statusBadge.toLowerCase()}`}>{statusBadge}</span>
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color: `var(--${color === 'amber' ? 'warn' : color === 'green' ? 'primary' : color === 'red' ? 'danger' : 'primary'})` }}>
        {value}
      </div>
      <div className="kpi-sub">{unit}</div>
      {sub && <div className="kpi-sub" style={{ marginTop: 2 }}>{sub}</div>}
      {delta && <div className={`kpi-delta kpi-${deltaType}`}>{delta}</div>}
    </div>
  )
}

// ── Alert Card ───────────────────────────────────────────────────────────────
function AlertCard({ alert, onResolve }) {
  const isSample = alert.is_sample_profile || alert.badge === 'Sample profile'
  return (
    <div className={`alert-card alert-${alert.severity}`}>
      <div className="alert-sev-dot" style={{ background: SEV_COLOR[alert.severity] }} />
      <div className="alert-body">
        <div className="alert-title" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span>{alert.title}</span>
          {isSample && <span className="badge badge-amber" style={{ fontSize: 10, padding: '2px 8px' }}>Sample profile</span>}
        </div>
        <div className="alert-desc">{alert.description}</div>
      </div>
      <div className="alert-right">
        <div className="alert-saving">₹{alert.potential_saving_inr.toLocaleString()}</div>
        <div className="alert-saving-label">/month</div>
        <span className={`badge badge-${alert.severity === 'high' ? 'red' : alert.severity === 'medium' ? 'amber' : 'green'}`} style={{ marginTop: 6 }}>
          {alert.severity.toUpperCase()}
        </span>
      </div>
      <button className="alert-resolve" onClick={() => onResolve(alert.id)} title="Mark resolved">✓</button>
    </div>
  )
}

// ── Copilot Panel ────────────────────────────────────────────────────────────
function Copilot({ kpis }) {
  const currentKwh = kpis?.kpis?.total_kwh || 48240
  const isCustom = kpis?.is_custom || (kpis?.data_source && !kpis.data_source.includes('demo_baseline'))
  const plantName = kpis?.plant || (isCustom ? 'My Industrial Facility' : 'Sample Plant')

  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [quickQs, setQuickQs] = useState([])
  const msgsContainerRef = useRef()

  useEffect(() => {
    const welcome = isCustom
      ? `Welcome to UrjaMind Copilot. Active telemetry for **${plantName}** (${currentKwh.toLocaleString()} kWh) is ready.\n\nAsk questions about equipment loads, tariff charges, or shift schedules.`
      : `Welcome to UrjaMind Copilot. Active telemetry for **${plantName}** is ready.\n\nCurrently analyzing operational parameters — explore equipment breakdown, off-peak shift savings, or carbon intensity.`
    setMsgs([{ role: 'bot', content: welcome }])
  }, [kpis?.plant, kpis?.kpis?.total_kwh, isCustom])

  useEffect(() => {
    fetchQuickQs()
      .then(setQuickQs)
      .catch(() =>
        setQuickQs([
          'Why did my bill increase?',
          'How can I save with ToD tariff?',
          'Check power factor penalty',
          'Estimated standby power draw'
        ])
      )
  }, [])

  useEffect(() => {
    if (msgsContainerRef.current) {
      msgsContainerRef.current.scrollTop = msgsContainerRef.current.scrollHeight
    }
  }, [msgs])

  async function send(text) {
    if (!text.trim() || loading) return
    setMsgs(m => [...m, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      const res = await chatWithCopilot(text)
      setMsgs(m => [...m, { role: 'bot', content: res.content }])
      logCopilotChat('plant_1', text, res.content, res.tool_called)
    } catch (err) {
      if (err?.response?.status === 401) {
        const isUserLoggedIn = Boolean(auth?.currentUser)
        setMsgs(m => [...m, {
          role: 'bot',
          content: isUserLoggedIn
            ? '⚠️ **Token Refreshing:** Cloud authentication is refreshing. Please try clicking the query again.'
            : '🔒 **Login Required:** Please click "Firebase Login" in the top bar to chat with Copilot.'
        }])
      } else {
        setMsgs(m => [...m, { role: 'bot', content: 'Could not reach the server. Please try again in a moment.' }])
      }
    } finally { setLoading(false) }
  }

  function renderContent(text) {
    return text.split('\n').map((line, i) => {
      const bold = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      return <p key={i} style={{ marginBottom: 4 }} dangerouslySetInnerHTML={{ __html: bold }} />
    })
  }

  return (
    <div className="copilot-panel">
      <div className="copilot-header">
        <div className="copilot-avatar">🤖</div>
        <div>
          <div className="copilot-name">UrjaMind Copilot</div>
          <div className="copilot-status">
            ● Online · {plantName} ({currentKwh.toLocaleString()} kWh)
          </div>
        </div>
      </div>
      <div className="copilot-quick">
        {quickQs.slice(0, 3).map((q, i) => (
          <button key={i} className="quick-q" onClick={() => send(q)}>{q}</button>
        ))}
      </div>
      <div className="copilot-msgs" ref={msgsContainerRef}>
        {msgs.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <div className="msg-bubble">{renderContent(m.content)}</div>
          </div>
        ))}
        {loading && <div className="msg msg-bot"><div className="msg-bubble typing">⏳ Analyzing...</div></div>}
      </div>
      <div className="copilot-input">
        <input
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send(input)}
          placeholder="Ask anything about your energy use..."
        />
        <button onClick={() => send(input)} disabled={loading} aria-label="Send message">➤</button>
      </div>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [kpis, setKpis] = useState(null)
  const [machines, setMachines] = useState([])
  const [baseline, setBaseline] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [nilm, setNilm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('Month')

  useEffect(() => {
    Promise.all([fetchKPIs(), fetchMachines(), fetchBaseline(), fetchAnomalies(), fetchNILM()])
      .then(([k, m, b, a, n]) => {
        setKpis(k)
        setMachines(m.machines)
        setBaseline(b)
        setAlerts(a.alerts)
        setNilm(n)
      })
      .catch(() => {
        setKpis({
          kpis: { total_kwh: 48240, specific_energy: 3.834, avg_power_factor: 0.870, pf_penalty_inr: 3200, md_penalty_inr: 0, total_amount_inr: 296500 },
          deviation_pct: 12.1,
          has_real_baseline: true,
        })
        setMachines([
          { machine: 'Induction Furnace (500 kg)', kwh: 21400, share_pct: 44.4, avg_pf: 0.91, status: 'normal' },
          { machine: 'Air Compressor (75 kW)', kwh: 8900, share_pct: 18.5, avg_pf: 0.85, status: 'idle_waste' },
          { machine: 'Hydraulic Press ×3', kwh: 6200, share_pct: 12.9, avg_pf: 0.88, status: 'degradation' },
          { machine: 'Fettling Machine ×6', kwh: 4800, share_pct: 9.9, avg_pf: 0.84, status: 'normal' },
          { machine: 'Lighting & HVAC', kwh: 6940, share_pct: 14.4, avg_pf: 0.80, status: 'pf_issue' },
        ])
        setBaseline({
          months: ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
          baseline_kwh_per_kg: [3.42, 3.42, 3.42, 3.42, 3.42, 3.42],
          actual_kwh_per_kg: [3.45, 3.50, 3.62, 3.75, 3.80, 3.83]
        })
        setAlerts([
          { id: 1, title: 'Estimated Compressor Idle Draw (11 PM – 3 AM)', description: 'Physics model estimates: 4.2 kW idle × ~4h × 22 nights = 370 kWh waste.', potential_saving_inr: 8400, severity: 'high' },
          { id: 2, title: 'Press Motor Drift', description: 'Specific energy trending +0.3%/day based on load profile model.', potential_saving_inr: 2800, severity: 'medium' },
          { id: 3, title: 'Power Factor Penalty — PF 0.870', description: 'Utility measured PF below 0.90 threshold -> penalty ₹3,200/month.', potential_saving_inr: 1200, severity: 'low' },
        ])
        setNilm({ status: 'SIMULATED', model: 'Physics simulation (Phase 1).' })
      })
      .finally(() => setLoading(false))
  }, [])

  function handleResolve(id) {
    resolveAnomaly(id).catch(() => { })
    setAlerts(a => a.filter(x => x.id !== id))
    toast.success('Alert resolved ✓')
  }

  const pieData = machines.map((m) => ({ name: m.machine.split(' (')[0], value: m.kwh, pct: m.share_pct }))
  const baselineData = baseline ? baseline.months.map((m, i) => ({
    month: m, Baseline: baseline.baseline_kwh_per_kg[i], Actual: baseline.actual_kwh_per_kg[i]
  })) : []

  // Check if a genuine distinct baseline exists
  const hasRealBaseline = Boolean(kpis?.has_real_baseline && !kpis?.is_custom)

  return (
    <div className="page">
      <div className="dash-layout">
        <div className="dash-main">
          {/* Header */}
          <div className="dash-header">
            <div>
              <h1 className="section-title">Energy Intelligence Dashboard</h1>
              <p style={{ color: 'var(--text2)', fontSize: 13, marginTop: 4, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>{kpis?.plant || 'Sample Manufacturing Facility'}</span>
                <span>·</span>
                <span>{kpis?.period || 'Sep 2026'}</span>
                <span>·</span>
                <span className={`badge ${kpis?.is_custom ? 'badge-green' : 'badge-blue'}`} style={{ fontSize: 11 }}>
                  {kpis?.is_custom ? `🟢 Data source: Uploaded Data (${kpis?.kpis?.total_kwh?.toLocaleString()} kWh)` : '⚡ Data source: Sample Plant (48,240 kWh)'}
                </span>
              </p>
            </div>
            <div className="time-tabs">
              {['Day', 'Week', 'Month'].map(t => (
                <button key={t} className={`time-tab ${timeRange === t ? 'time-tab-active' : ''}`} onClick={() => setTimeRange(t)}>{t}</button>
              ))}
            </div>
          </div>

          {/* 1. KPI ROW (FIRST) */}
          {loading ? (
            <div className="kpi-grid">
              {[1, 2, 3, 4].map(i => <div key={i} className="loading-skeleton" style={{ height: 120, borderRadius: 16 }} />)}
            </div>
          ) : kpis && (
            <div className="kpi-grid">
              <KpiCard
                label="Total Consumption"
                value={kpis.kpis.total_kwh.toLocaleString()}
                unit="kWh billing period"
                statusBadge="Measured"
                delta={hasRealBaseline && kpis.deviation_pct ? `${kpis.deviation_pct > 0 ? '↑' : '↓'} ${Math.abs(kpis.deviation_pct)}% vs baseline` : 'Utility billed volume'}
                deltaType={hasRealBaseline && kpis.deviation_pct > 0 ? 'warn' : 'up'}
                icon="⚡"
                color="blue"
              />
              <KpiCard
                label="Max Demand"
                value={`${kpis.kpis.max_demand_kva ?? 285} kVA`}
                unit="Billed maximum demand"
                statusBadge="Measured"
                delta={`Observed peak: ${kpis.kpis.observed_peak_kva ?? 253.3} kVA`}
                deltaType="up"
                icon="📈"
                color="amber"
              />
              <KpiCard
                label="Specific Energy"
                value={kpis.kpis.specific_energy}
                unit={kpis?.is_custom ? "kWh per unit produced" : "kWh per kg casting"}
                statusBadge={kpis?.is_custom ? "Estimated" : "Measured"}
                delta={
                  kpis?.production_extrapolation
                    ? kpis.production_extrapolation
                    : hasRealBaseline
                      ? `${kpis.deviation_pct}% vs baseline (3.42)`
                      : 'Production log calibrated'
                }
                deltaType={hasRealBaseline && kpis.deviation_pct > 0 ? "warn" : "up"}
                icon="🏷"
                color={hasRealBaseline && kpis.deviation_pct > 0 ? "amber" : "green"}
              />
              <KpiCard
                label="Power Factor"
                value={kpis.kpis.avg_power_factor}
                unit="Average (measured)"
                statusBadge="Measured"
                delta={(kpis.kpis.pf_penalty_inr || 0) > 0 ? `Penalty ₹${Math.round(kpis.kpis.pf_penalty_inr).toLocaleString()}` : 'No penalty (threshold ≥ 0.90)'}
                deltaType={(kpis.kpis.pf_penalty_inr || 0) > 0 ? 'warn' : 'up'}
                icon="📊"
                color="green"
              />
              <KpiCard
                label="Total Electricity Bill"
                value={`₹${Math.round(kpis.kpis.total_amount_inr || kpis.kpis.total_cost_inr || 296500).toLocaleString()}`}
                unit={kpis?.period || "Billing period"}
                statusBadge="Measured"
                delta={`₹${(kpis.kpis.total_kwh > 0 ? ((kpis.kpis.total_amount_inr || 296500) / kpis.kpis.total_kwh).toFixed(2) : '6.08')}/kWh blended rate`}
                deltaType="up"
                icon="💸"
                color="red"
              />
            </div>
          )}

          {/* 2. ALERTS ROW (SECOND) */}
          <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>⚠️ Anomalies & Waste Opportunities</span>
              <span className={`badge-status ${kpis?.is_custom && !kpis?.has_equipment ? 'badge-amber' : 'badge-estimated'}`}>
                {kpis?.is_custom && !kpis?.has_equipment ? 'Sample profile' : 'Estimated'}
              </span>
            </h3>
            <span className="badge badge-amber">
              {alerts.length} opportunities · ₹{alerts.reduce((s, a) => s + a.potential_saving_inr, 0).toLocaleString()}/month potential
            </span>
          </div>

          {/* Sample equipment profile notice banner */}
          {kpis?.is_custom && !kpis?.has_equipment && (
            <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 12, padding: '12px 16px', marginBottom: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 20 }}>📋</span>
                <span style={{ fontSize: 13, color: 'var(--text)' }}>
                  <strong>Sample Equipment Profile Active.</strong> Upload your equipment register to see machine-level results for {kpis?.plant || 'your plant'}.
                </span>
              </div>
              <a href="/upload" className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: 12, textDecoration: 'none', whiteSpace: 'nowrap' }}>
                Upload Equipment →
              </a>
            </div>
          )}

          <div className="alerts-list">
            {alerts.length > 0 ? (
              alerts.map(a => <AlertCard key={a.id} alert={a} onResolve={handleResolve} />)
            ) : (
              <div style={{ padding: 16, background: 'var(--surface)', borderRadius: 12, color: 'var(--text2)', fontSize: 13 }}>
                ✅ No unresolved anomalies detected. All parameters within expected thresholds.
              </div>
            )}
          </div>

          {/* 3. CHARTS ROW (THIRD) */}
          {(() => {
            const hours = Array.from({ length: 24 }, (_, i) => i)
            const dynamicLoadData = machines && machines.length > 0 ? hours.map(hr => {
              const isWorking = hr >= 8 && hr < 20
              const row = { hour: `${hr}:00` }
              machines.forEach((m, idx) => {
                const short = m.machine.replace('Production Machine ', '').replace('Plant ', '').split(' (')[0]
                const dailyAvg = (m.kwh / 26) / (isWorking ? 12 : 24)
                const wave = 0.85 + 0.3 * Math.sin(hr * 0.5 + idx * 1.5)
                row[short] = isWorking ? Math.max(0.5, Math.round(dailyAvg * wave * 10) / 10) : Math.max(0.1, Math.round(dailyAvg * 0.1 * 10) / 10)
              })
              return row
            }) : LOAD_DATA

            const machineKeys = machines && machines.length > 0
              ? machines.map(m => m.machine.replace('Production Machine ', '').replace('Plant ', '').split(' (')[0])
              : ['Furnace', 'Compressor', 'Press', 'Fettling', 'Misc']

            return (
              <div className="charts-row">
                <div className="chart-card" style={{ flex: 2, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div className="chart-title">24-Hour Diurnal Load Profile — Machine Disaggregation</div>
                    <span className="badge-status badge-simulated">Simulated</span>
                  </div>
                  <div className="chart-sub" style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 12 }}>
                    Physics prior allocation across {machines.length} active units (kW)
                  </div>
                  <ResponsiveContainer width="100%" height={230}>
                    <BarChart data={dynamicLoadData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="hour" tick={{ fill: 'var(--text3)', fontSize: 9 }} interval={3} />
                      <YAxis tick={{ fill: 'var(--text3)', fontSize: 10 }} unit=" kW" />
                      <Tooltip contentStyle={{ background: '#0b2a1f', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 10, fontSize: 12, color: '#ecfdf5' }} />
                      <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text2)' }} />
                      {machineKeys.map((key, i) => (
                        <Bar
                          key={key}
                          dataKey={key}
                          stackId="a"
                          fill={COLORS[i % COLORS.length]}
                          radius={i === machineKeys.length - 1 ? [3, 3, 0, 0] : [0, 0, 0, 0]}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="chart-card" style={{ flex: 1, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div className="chart-title">Energy Share</div>
                    <span className="badge-status badge-estimated">Estimated</span>
                  </div>
                  <div className="chart-sub" style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 12 }}>
                    Disaggregated machine share — {kpis?.period || 'Period'}
                  </div>
                  <ResponsiveContainer width="100%" height={230}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" paddingAngle={2}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v, n) => [`${v.toLocaleString()} kWh`, n]} contentStyle={{ background: '#0b2a1f', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 10, fontSize: 12, color: '#ecfdf5' }} />
                      <Legend wrapperStyle={{ fontSize: 10, color: 'var(--text2)' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )
          })()}

          {/* 4. MACHINE TABLE + BASELINE TREND (FOURTH) */}
          <div className="charts-row">
            <div className="chart-card" style={{ flex: 1.2, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <div className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>Machine Telemetry Register</span>
                  {kpis?.is_custom && !kpis?.has_equipment && (
                    <span className="badge badge-amber" style={{ fontSize: 10 }}>Sample profile</span>
                  )}
                </div>
                <span className={`badge-status ${kpis?.is_custom && !kpis?.has_equipment ? 'badge-amber' : 'badge-estimated'}`}>
                  {kpis?.is_custom && !kpis?.has_equipment ? 'Sample profile' : 'Estimated'}
                </span>
              </div>
              <div className="chart-sub" style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 12 }}>
                {kpis?.is_custom && !kpis?.has_equipment
                  ? `Upload your equipment register to see machine-level results for ${kpis?.plant || 'your plant'}`
                  : 'Consumption disaggregated across registered equipment'}
              </div>
              <table className="machine-table">
                <thead><tr><th>Machine</th><th>kWh</th><th>Share</th><th>PF</th><th>Status</th></tr></thead>
                <tbody>
                  {machines.map((m, i) => (
                    <tr key={i}>
                      <td style={{ fontSize: 12 }}>
                        {m.machine.split(' (')[0]}
                        {(m.is_sample_profile || (!kpis?.has_equipment && kpis?.is_custom)) && (
                          <span className="badge badge-amber" style={{ fontSize: 9, marginLeft: 6, padding: '1px 5px' }}>Sample</span>
                        )}
                      </td>
                      <td style={{ fontWeight: 700 }}>{m.kwh.toLocaleString()}</td>
                      <td>
                        <div className="mini-bar"><div className="mini-fill" style={{ width: `${m.share_pct * 2}%`, background: COLORS[i % COLORS.length] }} /></div>
                      </td>
                      <td><span className={`badge ${m.avg_pf >= 0.90 ? 'badge-green' : m.avg_pf >= 0.85 ? 'badge-amber' : 'badge-red'}`}>{m.avg_pf}</span></td>
                      <td style={{ fontSize: 11, color: m.status === 'idle_waste' ? 'var(--warn)' : m.status === 'degradation' ? 'var(--danger)' : 'var(--text2)' }}>
                        {m.status === 'idle_waste' ? '⚠️ Standby' : m.status === 'degradation' ? '📉 Drift' : m.status === 'pf_issue' ? '⚡ Low PF' : '✅ Nominal'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="chart-card" style={{ flex: 1, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <div className="chart-title">
                  {kpis?.is_custom ? 'Production Calibration Target' : 'Specific Energy Baseline Trend'}
                </div>
                <span className="badge-status badge-measured">Measured</span>
              </div>
              <div className="chart-sub" style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 12 }}>
                {kpis?.is_custom
                  ? `Specific Energy Target: ${kpis.kpis.specific_energy} kWh/unit`
                  : 'Expected vs actual kWh/kg (production-adjusted)'}
              </div>
              <ResponsiveContainer width="100%" height={230}>
                {kpis?.is_custom ? (
                  <LineChart data={[
                    { month: 'Target', Target: kpis.kpis.specific_energy, Measured: kpis.kpis.specific_energy },
                    { month: kpis.period || 'Sep', Target: kpis.kpis.specific_energy, Measured: kpis.kpis.specific_energy },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" tick={{ fill: 'var(--text3)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text3)', fontSize: 10 }} unit=" kWh/u" domain={[0, Math.ceil(kpis.kpis.specific_energy * 1.5)]} />
                    <Tooltip contentStyle={{ background: '#0b2a1f', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 10, fontSize: 12, color: '#ecfdf5' }} />
                    <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text2)' }} />
                    <Line type="monotone" dataKey="Target" stroke="var(--primary)" strokeWidth={2} dot={{ r: 5 }} />
                    <Line type="monotone" dataKey="Measured" stroke="var(--accent-lime)" strokeWidth={2} dot={{ r: 5 }} />
                  </LineChart>
                ) : (
                  <LineChart data={baselineData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" tick={{ fill: 'var(--text3)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text3)', fontSize: 10 }} unit=" kWh/kg" domain={[3.3, 4.0]} />
                    <Tooltip contentStyle={{ background: '#0b2a1f', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 10, fontSize: 12, color: '#ecfdf5' }} />
                    <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text2)' }} />
                    <Line type="monotone" dataKey="Baseline" stroke="var(--primary)" strokeWidth={2} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="Actual" stroke="var(--danger)" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Copilot sidebar */}
        <Copilot kpis={kpis} />
      </div>
    </div>
  )
}

