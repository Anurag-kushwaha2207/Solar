import { useState, useEffect, useRef } from 'react'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import toast from 'react-hot-toast'
import { fetchKPIs, fetchMachines, fetchBaseline, fetchAnomalies, fetchNILM, chatWithCopilot, fetchQuickQs, resolveAnomaly } from '../api'
import { logCopilotChat } from '../firebase'
import './Dashboard.css'


const COLORS = ['#3b9eff','#f6a623','#38d9a9','#a78bfa','#fb7185']
const SEV_COLOR = { high:'var(--red)', medium:'var(--amber)', low:'var(--blue-light)' }

// ── Load Profile data (synthetic 24h) ───────────────────────────────────────
function genLoadProfile() {
  const h = Array.from({length:24},(_,i)=>i)
  return h.map(hr => ({
    hour:`${hr}:00`,
    Furnace:  hr>=6&&hr<22 ? 120+Math.random()*40 : 6,
    Compressor: hr>=6&&hr<22 ? 38+Math.random()*18 : 4.2,
    Press:    hr>=6&&hr<18 ? 55+Math.random()*20 : 1,
    Fettling: hr>=6&&hr<18 ? 30+Math.random()*14 : 0.5,
    Misc:     8+Math.random()*6,
  }))
}
const LOAD_DATA = genLoadProfile()

// ── KPI Card ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, unit, sub, delta, deltaType, icon, color }) {
  return (
    <div className={`kpi-card kpi-${color}`}>
      <div className="kpi-icon">{icon}</div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{color:`var(--${color==='amber'?'amber':color==='green'?'green':color==='red'?'red':'blue-light'})`}}>
        {value}
      </div>
      <div className="kpi-sub">{unit}</div>
      {sub && <div className="kpi-sub" style={{marginTop:2}}>{sub}</div>}
      {delta && <div className={`kpi-delta kpi-${deltaType}`}>{delta}</div>}
    </div>
  )
}

// ── Alert Card ───────────────────────────────────────────────────────────────
function AlertCard({ alert, onResolve }) {
  return (
    <div className={`alert-card alert-${alert.severity}`}>
      <div className="alert-sev-dot" style={{background:SEV_COLOR[alert.severity]}} />
      <div className="alert-body">
        <div className="alert-title">{alert.title}</div>
        <div className="alert-desc">{alert.description}</div>
      </div>
      <div className="alert-right">
        <div className="alert-saving">₹{alert.potential_saving_inr.toLocaleString()}</div>
        <div className="alert-saving-label">/month</div>
        <span className={`badge badge-${alert.severity==='high'?'red':alert.severity==='medium'?'amber':'blue'}`} style={{marginTop:6}}>
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
  const isCustom = kpis?.data_source && !kpis.data_source.includes('demo_baseline')

  const [msgs, setMsgs] = useState([{
    role:'bot',
    content: isCustom
      ? `Namaste! 🙏 Main aapka UrjaMind Copilot hun. Uploaded plant data (${currentKwh.toLocaleString()} kWh) analyze ho gaya hai.\n\nLive analytical tools execute karke instant answers deta hun. Koi bhi sawaal pucho!`
      : 'Namaste! 🙏 Main aapka UrjaMind Copilot hun. Rajkot Foundry ka data analyze ho gaya hai.\n\nIs mahine **3 operational anomalies** detect hui hain — potential saving: **₹12,400/month** (Scheduler tab mein ToD optimization se ₹47,500/month alag se potential hai).\n\nKoi bhi sawaal pucho!'
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [quickQs, setQuickQs] = useState([])
  const endRef = useRef()

  useEffect(() => {
    fetchQuickQs().then(setQuickQs).catch(() =>
      setQuickQs(['Bill kyun badha?','Compressor problem?','Total saving kitna?','Carbon report?'])
    )
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView({behavior:'smooth'}) }, [msgs])

  async function send(text) {
    if (!text.trim() || loading) return
    setMsgs(m => [...m, {role:'user', content:text}])
    setInput('')
    setLoading(true)
    try {
      const res = await chatWithCopilot(text)
      setMsgs(m => [...m, {role:'bot', content:res.content}])
      // Log to Firestore in background
      logCopilotChat('plant_1', text, res.content, res.tool_called)
    } catch {
      setMsgs(m => [...m, {role:'bot', content:'Connection error — backend chal raha hai? `cd backend && python -m uvicorn main:app --reload --port 8000`'}])
    } finally { setLoading(false) }
  }

  function renderContent(text) {
    return text.split('\n').map((line, i) => {
      const bold = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      return <p key={i} style={{marginBottom:4}} dangerouslySetInnerHTML={{__html:bold}} />
    })
  }

  return (
    <div className="copilot-panel">
      <div className="copilot-header">
        <div className="copilot-avatar">🤖</div>
        <div>
          <div className="copilot-name">UrjaMind Copilot</div>
          <div className="copilot-status">
            ● Online · {isCustom ? `Active: ${currentKwh.toLocaleString()} kWh` : 'Demo (48,240 kWh)'}
          </div>
        </div>
      </div>
      <div className="copilot-quick">
        {quickQs.slice(0,3).map((q,i) => (
          <button key={i} className="quick-q" onClick={() => send(q)}>{q}</button>
        ))}
      </div>
      <div className="copilot-msgs">
        {msgs.map((m,i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <div className="msg-bubble">{renderContent(m.content)}</div>
          </div>
        ))}
        {loading && <div className="msg msg-bot"><div className="msg-bubble typing">⏳ Analyzing...</div></div>}
        <div ref={endRef} />
      </div>
      <div className="copilot-input">
        <input
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key==='Enter' && send(input)}
          placeholder="Koi bhi sawaal pucho..."
        />
        <button onClick={() => send(input)} disabled={loading}>➤</button>
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
  const [timeRange, setTimeRange] = useState('Week')

  useEffect(() => {
    Promise.all([fetchKPIs(), fetchMachines(), fetchBaseline(), fetchAnomalies(), fetchNILM()])
      .then(([k, m, b, a, n]) => {
        setKpis(k); setMachines(m.machines); setBaseline(b)
        setAlerts(a.alerts); setNilm(n)
      })
      .catch(() => {
        // Fallback demo data — consistent with backend/constants.py
        setKpis({ kpis:{total_kwh:48240,specific_energy:3.834,avg_power_factor:0.870,pf_penalty_inr:3200,md_penalty_inr:0,total_amount_inr:296500}, deviation_pct:12.1 })
        setMachines([
          {machine:'Induction Furnace (500 kg)',kwh:21400,share_pct:44.4,avg_pf:0.91,status:'normal'},
          {machine:'Air Compressor (75 kW)',     kwh:8900, share_pct:18.5,avg_pf:0.85,status:'idle_waste'},
          {machine:'Hydraulic Press ×3',         kwh:6200, share_pct:12.9,avg_pf:0.88,status:'degradation'},
          {machine:'Fettling Machine ×6',        kwh:4800, share_pct:9.9, avg_pf:0.84,status:'normal'},
          {machine:'Lighting & HVAC',            kwh:6940, share_pct:14.4,avg_pf:0.80,status:'pf_issue'},
        ])
        setBaseline({months:['Apr','May','Jun','Jul','Aug','Sep'],
          baseline_kwh_per_kg:[3.42,3.42,3.42,3.42,3.42,3.42],
          actual_kwh_per_kg:  [3.45,3.50,3.62,3.75,3.80,3.83]})
        setAlerts([
          {id:1,title:'Idle Compressor — Raat 11PM–3AM',description:'Physics model: 4.2 kW idle × ~4h × 22 nights = 370 kWh waste.',potential_saving_inr:8400,severity:'high'},
          {id:2,title:'Press #3 Motor Degradation',description:'Specific energy trending +0.3%/day (physics sim).',potential_saving_inr:2800,severity:'medium'},
          {id:3,title:'Power Factor Drop — PF 0.870',description:'DISCOM measured PF → penalty ₹3,200/month.',potential_saving_inr:1200,severity:'low'},
        ])
        setNilm({status:'SIMULATED', model:'Physics simulation (Phase 1). ML training planned Phase 2.'})
      })
      .finally(() => setLoading(false))
  }, [])

  function handleResolve(id) {
    resolveAnomaly(id).catch(()=>{})
    setAlerts(a => a.filter(x => x.id !== id))
    toast.success('Alert resolved ✓')
  }

  const pieData = machines.map((m,i) => ({ name:m.machine.split(' (')[0], value:m.kwh, pct:m.share_pct }))
  const baselineData = baseline ? baseline.months.map((m,i) => ({
    month:m, Baseline:baseline.baseline_kwh_per_kg[i], Actual:baseline.actual_kwh_per_kg[i]
  })) : []

  return (
    <div className="page">
      <div className="dash-layout">
        <div className="dash-main">
          {/* Header */}
          <div className="dash-header">
            <div>
              <h1 className="section-title">Energy Intelligence Dashboard</h1>
              <p style={{color:'var(--text2)',fontSize:13,marginTop:4}}>
                Rajkot Foundry · Sep 2026 ·{' '}
                {nilm && (
                  <span className={`badge ${nilm.status==='SIMULATED'?'badge-amber':'badge-green'}`}>
                    {nilm.status==='SIMULATED' ? '🔬 Physics Simulation (Phase 1)' : '🎯 ML Model Active'}
                  </span>
                )}
              </p>
              <div style={{marginTop:6,padding:'6px 10px',background:'rgba(246,166,35,0.08)',border:'1px solid rgba(246,166,35,0.25)',borderRadius:8,fontSize:11,color:'var(--amber)',display:'inline-block'}}>
                ⚠ Demo: Physics simulation data — not from trained ML model
              </div>
            </div>
            <div className="time-tabs">
              {['Day','Week','Month'].map(t => (
                <button key={t} className={`time-tab ${timeRange===t?'time-tab-active':''}`} onClick={() => setTimeRange(t)}>{t}</button>
              ))}
            </div>
          </div>

          {/* KPIs */}
          {loading ? (
            <div className="kpi-grid">
              {[1,2,3,4].map(i => <div key={i} className="loading-skeleton" style={{height:120,borderRadius:16}} />)}
            </div>
          ) : kpis && (
            <div className="kpi-grid">
              <KpiCard label="Total Consumption" value={kpis.kpis.total_kwh.toLocaleString()} unit="kWh this month" delta="↑ 12.1% above baseline" deltaType="up" icon="⚡" color="blue" />
              <KpiCard label="Specific Energy" value={kpis.kpis.specific_energy} unit="kWh per kg casting" delta={`⚠ ${kpis.deviation_pct}% above baseline (3.42)`} deltaType="warn" icon="🏷" color="amber" />
              <KpiCard label="Power Factor" value={kpis.kpis.avg_power_factor} unit="Avg this month" delta={`PF Penalty ₹${(kpis.kpis.pf_penalty_inr||0).toLocaleString()}`} deltaType="warn" icon="📊" color="green" />
              <KpiCard label="Total Bill" value={`₹${((kpis.kpis.total_amount_inr||kpis.kpis.total_cost_inr||296500)/1000).toFixed(0)}K`} unit="Sep 2026" delta="₹6.08/kWh blended" deltaType="up" icon="💸" color="red" />
            </div>
          )}

          {/* Charts row */}
          <div className="charts-row">
            <div className="chart-card" style={{flex:2}}>
              <div className="chart-title">24-Hour Load Profile — Machine Disaggregation (NILM)</div>
              <div className="chart-sub">AI-estimated machine-level breakdown from total meter signal</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={LOAD_DATA} margin={{top:4,right:8,bottom:0,left:0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="hour" tick={{fill:'#4a6580',fontSize:9}} interval={3} />
                  <YAxis tick={{fill:'#4a6580',fontSize:10}} unit=" kW" />
                  <Tooltip contentStyle={{background:'#0d1a2e',border:'1px solid rgba(99,179,237,0.25)',borderRadius:10,fontSize:12}} />
                  <Legend wrapperStyle={{fontSize:11,color:'#8ba7c7'}} />
                  <Bar dataKey="Furnace"    stackId="a" fill="rgba(59,158,255,0.75)"  />
                  <Bar dataKey="Compressor" stackId="a" fill="rgba(246,166,35,0.75)" />
                  <Bar dataKey="Press"      stackId="a" fill="rgba(56,217,169,0.75)" />
                  <Bar dataKey="Fettling"   stackId="a" fill="rgba(167,139,250,0.75)"/>
                  <Bar dataKey="Misc"       stackId="a" fill="rgba(251,113,133,0.75)" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card" style={{flex:1}}>
              <div className="chart-title">Energy Breakdown</div>
              <div className="chart-sub">By machine — Sep 2026</div>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" paddingAngle={2}>
                    {pieData.map((_,i) => <Cell key={i} fill={COLORS[i%COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v,n) => [`${v.toLocaleString()} kWh`,n]} contentStyle={{background:'#0d1a2e',border:'1px solid rgba(99,179,237,0.25)',borderRadius:10,fontSize:12}} />
                  <Legend wrapperStyle={{fontSize:10,color:'#8ba7c7'}} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Anomaly Alerts */}
          <div className="section-header">
            <h3 style={{fontSize:16,fontWeight:700}}>⚠️ Anomalies & Waste Detected</h3>
            <span className="badge badge-red">{alerts.length} alerts · ₹{alerts.reduce((s,a)=>s+a.potential_saving_inr,0).toLocaleString()}/mo potential</span>
          </div>
          <div className="alerts-list">
            {alerts.map(a => <AlertCard key={a.id} alert={a} onResolve={handleResolve} />)}
          </div>

          {/* Machine table + Baseline */}
          <div className="charts-row" style={{marginTop:20}}>
            <div className="chart-card" style={{flex:1.2}}>
              <div className="chart-title">Machine-Level Breakdown</div>
              <div className="chart-sub">AI-estimated energy per equipment</div>
              <table className="machine-table">
                <thead><tr><th>Machine</th><th>kWh</th><th>Share</th><th>PF</th><th>Status</th></tr></thead>
                <tbody>
                  {machines.map((m,i) => (
                    <tr key={i}>
                      <td style={{fontSize:12}}>{m.machine.split(' (')[0]}</td>
                      <td style={{fontWeight:700}}>{m.kwh.toLocaleString()}</td>
                      <td>
                        <div className="mini-bar"><div className="mini-fill" style={{width:`${m.share_pct*2}%`,background:COLORS[i%COLORS.length]}} /></div>
                      </td>
                      <td><span className={`badge ${m.avg_pf>=0.90?'badge-green':m.avg_pf>=0.85?'badge-amber':'badge-red'}`}>{m.avg_pf}</span></td>
                      <td style={{fontSize:11,color:m.status==='idle_waste'?'var(--amber)':m.status==='degradation'?'var(--red)':'var(--text3)'}}>
                        {m.status==='idle_waste'?'⚠️ Idle':m.status==='degradation'?'📉 Drift':m.status==='pf_issue'?'⚡ PF':'✅ OK'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="chart-card" style={{flex:1}}>
              <div className="chart-title">Baseline vs Actual — Specific Energy</div>
              <div className="chart-sub">Expected vs actual kWh/kg (production-adjusted)</div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={baselineData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" tick={{fill:'#4a6580',fontSize:11}} />
                  <YAxis tick={{fill:'#4a6580',fontSize:10}} unit=" kWh/kg" domain={[3.3,4.0]} />
                  <Tooltip contentStyle={{background:'#0d1a2e',border:'1px solid rgba(99,179,237,0.25)',borderRadius:10,fontSize:12}} />
                  <Legend wrapperStyle={{fontSize:11,color:'#8ba7c7'}} />
                  <Line type="monotone" dataKey="Baseline" stroke="#3b9eff" strokeWidth={2} dot={{r:4}} />
                  <Line type="monotone" dataKey="Actual"   stroke="#ff6b6b" strokeWidth={2} dot={{r:4}} strokeDasharray="0" />
                </LineChart>
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
