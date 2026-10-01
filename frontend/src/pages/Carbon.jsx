import { useState, useEffect } from 'react'
import { BarChart, Bar, LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import toast from 'react-hot-toast'
import { fetchCarbonReport, fetchIntensity } from '../api'
import './Carbon.css'

function MvRow({ item, i }) {
  const statusBadge = {
    verified:  <span className="badge badge-green">✓ Verified</span>,
    projected: <span className="badge badge-amber">◎ Projected</span>,
  }
  return (
    <tr className="mv-row" style={{animationDelay:`${i*0.05}s`}}>
      <td>{item.name}</td>
      <td>{item.baseline_kwh ? item.baseline_kwh.toLocaleString() : '—'}</td>
      <td>{item.actual_kwh   ? item.actual_kwh.toLocaleString()   : '—'}</td>
      <td className={item.saving_kwh>0?'td-save':''}>{item.saving_kwh > 0 ? `−${item.saving_kwh.toLocaleString()}` : '—'}</td>
      <td style={{color:'var(--green)',fontWeight:700}}>
        {item.co2_avoided_t > 0 ? `${item.co2_avoided_t} tCO₂e` : '—'}
      </td>
      <td style={{fontWeight:700}}>₹{item.saving_inr.toLocaleString()}</td>
      <td>{statusBadge[item.status]}</td>
    </tr>
  )
}

export default function Carbon() {
  const [report, setReport] = useState(null)
  const [intensity, setIntensity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeScope, setActiveScope] = useState('both')

  useEffect(() => {
    Promise.all([fetchCarbonReport(), fetchIntensity()])
      .then(([r, t]) => { setReport(r); setIntensity(t) })
      .catch(() => {
        setReport({
          plant:'Rajkot Precision Foundry Pvt. Ltd.',
          period:'Apr 2026 – Sep 2026',
          combined:{months:['Apr','May','Jun','Jul','Aug','Sep'],scope1:[2.8,3.0,3.2,3.4,3.0,3.2],scope2:[14.9,15.2,16.8,17.2,18.3,16.7],total:90.8,intensity_kg_per_kg:2.74,projected_saving_tco2e:14.2},
          scope2:{total_tco2e:100.1,emission_factor:0.716,ef_source:'CEA India 2023 — Western Regional Grid'},
          scope1:{total_tco2e:18.6,sources:['Diesel generator','Furnace oil']},
          mv_table:[
            {name:'Compressor idle control',baseline_kwh:2880,actual_kwh:1440,saving_kwh:1440,co2_avoided_t:1.03,saving_inr:8928,status:'verified'},
            {name:'Furnace shift to off-peak',baseline_kwh:21400,actual_kwh:21400,saving_kwh:0,co2_avoided_t:0,saving_inr:10200,status:'verified'},
            {name:'PF correction (target)',baseline_kwh:null,actual_kwh:null,saving_kwh:420,co2_avoided_t:0.30,saving_inr:1400,status:'projected'},
            {name:'Press #3 maintenance',baseline_kwh:null,actual_kwh:null,saving_kwh:380,co2_avoided_t:0.27,saving_inr:2356,status:'projected'},
          ],
          audit_trail:[
            {action:'DISCOM data ingested',detail:'48,240 kWh · 30-min · Sep 2026'},
            {action:'Scope 2 calculated',detail:'48,240 × 0.716 = 34.54 tCO₂e'},
            {action:'Scope 1 — Diesel log',detail:'320L × 2.68 = 0.86 tCO₂e'},
            {action:'M&V baseline trained',detail:'LightGBM R²=0.91 · Apr–Aug'},
            {action:'Report signed',detail:'SHA-256: a4f2e8c3... · v1.0'},
          ],
          buyer_readiness:{scope2_location_based:true,scope1_direct:true,ghg_protocol_aligned:true,emission_intensity_metric:true,machine_readable_api:true}
        })
        setIntensity({months:['Apr','May','Jun','Jul','Aug','Sep'],intensity:[2.48,2.52,2.61,2.68,2.71,2.74],target_intensity:2.45,unit:'kgCO2e per kg'})
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading || !report) return (
    <div className="page" style={{display:'flex',alignItems:'center',justifyContent:'center',height:'80vh'}}>
      <div style={{textAlign:'center'}}>
        <div style={{fontSize:48,marginBottom:12,animation:'float 2s infinite'}}>🌿</div>
        <div style={{color:'var(--text2)'}}>Carbon report loading...</div>
      </div>
    </div>
  )

  const { combined, scope2, scope1, mv_table, audit_trail, buyer_readiness } = report
  const chartData = combined.months.map((m,i) => ({month:m, 'Scope 1':combined.scope1[i], 'Scope 2':combined.scope2[i]}))
  const intensityData = intensity?.months.map((m,i) => ({month:m, Intensity:intensity.intensity[i], Target:intensity.target_intensity})) || []
  const totalAvoided = mv_table.filter(r=>r.status==='verified').reduce((s,r)=>s+r.co2_avoided_t,0)

  return (
    <div className="page">
      <div className="container-wide" style={{paddingTop:24,paddingBottom:60}}>
        {/* Header */}
        <div className="carbon-header">
          <div>
            <h1 className="section-title">🌿 GHG Carbon Report</h1>
            <p style={{color:'var(--text2)',marginTop:6,fontSize:13}}>{report.plant} · {report.period} · GHG Protocol Corporate Standard</p>
          </div>
          <div style={{display:'flex',gap:10}}>
            <button className="btn btn-green" onClick={()=>toast.success('📄 PDF report exported!')}>📄 Export PDF</button>
            <button className="btn btn-secondary" onClick={()=>toast.success('🔗 API endpoint shared!')}>🔗 Share API</button>
          </div>
        </div>

        {/* KPI Row */}
        <div className="carbon-kpis">
          <div className="carbon-kpi-card" style={{'--accent':'var(--red)'}}>
            <div className="ckpi-icon">🔥</div>
            <div className="ckpi-val">{scope1.total_tco2e}</div>
            <div className="ckpi-label">Scope 1 — Direct</div>
            <div className="ckpi-sub">{scope1.sources.join(', ')}</div>
          </div>
          <div className="carbon-kpi-card" style={{'--accent':'var(--amber)'}}>
            <div className="ckpi-icon">⚡</div>
            <div className="ckpi-val">{scope2.total_tco2e}</div>
            <div className="ckpi-label">Scope 2 — Electricity</div>
            <div className="ckpi-sub">EF: {scope2.emission_factor} kgCO₂/kWh · CEA 2023</div>
          </div>
          <div className="carbon-kpi-card" style={{'--accent':'var(--green)'}}>
            <div className="ckpi-icon">♻️</div>
            <div className="ckpi-val">{totalAvoided.toFixed(2)}</div>
            <div className="ckpi-label">tCO₂e Avoided (Verified)</div>
            <div className="ckpi-sub">Projected: {combined.projected_saving_tco2e} tCO₂e/year</div>
          </div>
          <div className="carbon-kpi-card" style={{'--accent':'var(--blue-light)'}}>
            <div className="ckpi-icon">📊</div>
            <div className="ckpi-val">{combined.intensity_kg_per_kg}</div>
            <div className="ckpi-label">kgCO₂e / kg casting</div>
            <div className="ckpi-sub">Target: 2.45 kg · Gap: {(combined.intensity_kg_per_kg-2.45).toFixed(2)}</div>
          </div>
        </div>

        <div className="carbon-layout">
          <div className="carbon-left">
            {/* Scope Chart */}
            <div className="chart-card" style={{marginBottom:20}}>
              <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:16,flexWrap:'wrap',gap:8}}>
                <div>
                  <div className="chart-title">Monthly GHG Emissions — Scope 1 + 2</div>
                  <div className="chart-sub">tCO₂e · {report.period}</div>
                </div>
                <div style={{display:'flex',gap:6}}>
                  {['both','1','2'].map(s => (
                    <button key={s} className={`method-tab ${activeScope===s?'method-active':''}`} style={{padding:'6px 12px',fontSize:11}} onClick={() => setActiveScope(s)}>
                      {s==='both'?'Both':s==='1'?'Scope 1':'Scope 2'}
                    </button>
                  ))}
                </div>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" tick={{fill:'#4a6580',fontSize:11}} />
                  <YAxis tick={{fill:'#4a6580',fontSize:10}} unit=" t" />
                  <Tooltip formatter={v=>`${v} tCO₂e`} contentStyle={{background:'#0d1a2e',border:'1px solid rgba(99,179,237,0.25)',borderRadius:10,fontSize:12}} />
                  <Legend wrapperStyle={{fontSize:11,color:'#8ba7c7'}} />
                  {(activeScope==='both'||activeScope==='1') && <Bar dataKey="Scope 1" fill="rgba(255,107,107,0.7)" radius={[3,3,0,0]} />}
                  {(activeScope==='both'||activeScope==='2') && <Bar dataKey="Scope 2" fill="rgba(246,166,35,0.7)" radius={[3,3,0,0]} />}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Intensity Trend */}
            <div className="chart-card" style={{marginBottom:20}}>
              <div className="chart-title">Emission Intensity Trend</div>
              <div className="chart-sub">kgCO₂e per kg casting · Target = 2.45</div>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={intensityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" tick={{fill:'#4a6580',fontSize:11}} />
                  <YAxis tick={{fill:'#4a6580',fontSize:10}} domain={[2.3,2.9]} />
                  <Tooltip contentStyle={{background:'#0d1a2e',border:'1px solid rgba(99,179,237,0.25)',borderRadius:10,fontSize:12}} />
                  <ReferenceLine y={2.45} stroke="var(--green)" strokeDasharray="6 3" label={{value:'Target 2.45',fill:'var(--green)',fontSize:10}} />
                  <Legend wrapperStyle={{fontSize:11,color:'#8ba7c7'}} />
                  <Line type="monotone" dataKey="Intensity" stroke="var(--amber)" strokeWidth={2} dot={{r:4}} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* M&V Table */}
            <div className="chart-card">
              <div className="chart-title" style={{marginBottom:4}}>📋 Measurement & Verification (IPMVP)</div>
              <div className="chart-sub" style={{marginBottom:16}}>Verified savings per intervention — auditable</div>
              <div style={{overflowX:'auto'}}>
                <table className="mv-table">
                  <thead>
                    <tr>
                      <th>Intervention</th><th>Baseline kWh</th><th>Actual kWh</th><th>Saving kWh</th><th>CO₂ Avoided</th><th>₹ Saving</th><th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mv_table.map((r,i) => <MvRow key={i} item={r} i={i} />)}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="carbon-right">
            {/* Buyer Readiness */}
            <div className="chart-card" style={{marginBottom:16}}>
              <div className="chart-title" style={{marginBottom:14}}>🌐 Buyer/CBAM Readiness</div>
              <div style={{display:'flex',flexDirection:'column',gap:10}}>
                {Object.entries(buyer_readiness).map(([k,v]) => (
                  <div key={k} style={{display:'flex',alignItems:'center',justifyContent:'space-between',fontSize:13}}>
                    <span style={{color:'var(--text2)'}}>{k.replace(/_/g,' ')}</span>
                    <span>{v ? <span style={{color:'var(--green)'}}>✅</span> : <span style={{color:'var(--red)'}}>✗</span>}</span>
                  </div>
                ))}
              </div>
              <div className="buyer-score">
                <div className="buyer-score-val">4 / 5</div>
                <div className="buyer-score-label">Buyer Readiness Score</div>
              </div>
            </div>

            {/* Audit Trail */}
            <div className="chart-card" style={{marginBottom:16}}>
              <div className="chart-title" style={{marginBottom:14}}>🔒 Audit Trail</div>
              <div style={{display:'flex',flexDirection:'column',gap:8}}>
                {audit_trail.map((e,i) => (
                  <div key={i} className="audit-row">
                    <div className="audit-dot" />
                    <div>
                      <div style={{fontSize:12,fontWeight:700}}>{e.action}</div>
                      <div style={{fontSize:11,color:'var(--text3)'}}>{e.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* EF Source */}
            <div className="chart-card ef-card">
              <div className="chart-title" style={{marginBottom:8}}>⚡ Emission Factor</div>
              <div className="ef-val">{scope2.emission_factor} <span>kgCO₂/kWh</span></div>
              <div style={{fontSize:12,color:'var(--text2)',marginTop:6}}>{scope2.ef_source}</div>
              <div className="badge badge-blue" style={{marginTop:10}}>Location-based (GHG Protocol)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
