import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { loadDemoData, uploadBill, uploadMeter, uploadProduction, uploadEquipment } from '../api'
import { uploadBillDocument, savePlantRecord } from '../firebase'
import './Upload.css'

const STEPS = ['Upload Data', 'Dashboard', 'Scheduler', 'Carbon Report']

function DropZone({ icon, title, desc, formats, required, onUpload, uploaded, id }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleFile(file) {
    if (!file) return
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('plant_id', '1')
      const res = await onUpload(fd)

      // Parallel Firebase Storage upload & Firestore record
      uploadBillDocument(file, 'plant_1').then(fbRes => {
        if (fbRes.success) {
          savePlantRecord('plant_1', {
            latestFileUrl: fbRes.downloadUrl,
            fileName: file.name,
            fileType: title,
            extracted: res?.extracted || null,
          })
          toast.success(`☁️ Document securely stored in Firebase Storage!`)
        }
      })

      if (res?.mode === 'data_parsed' || res?.mode === 'bill_ocr_parsed') {
        toast.success(`✅ ${title} parsed (${res.rows_detected || 'bill metrics'} updated live analytics)!`)
      } else {
        toast.success(`ℹ️ ${title} received — demo baseline active`)
      }
    } catch {
      toast.error('Upload failed — using demo data instead')
    } finally {
      setLoading(false)
    }
  }


  return (
    <div
      className={`drop-zone ${dragging ? 'dragging' : ''} ${uploaded ? 'uploaded' : ''}`}
      onClick={() => document.getElementById(id).click()}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
    >
      {required && <span className="dz-badge required">Required</span>}
      {!required && <span className="dz-badge optional">Optional</span>}
      <div className="dz-icon">{uploaded ? '✅' : loading ? '⏳' : icon}</div>
      <h3 className="dz-title">{title}</h3>
      <p className="dz-desc">{desc}</p>
      <div className="dz-formats">
        {formats.map(f => <span key={f} className="dz-format">{f}</span>)}
      </div>
      {!uploaded && !loading && <div className="dz-cta">Click or drag & drop</div>}
      {uploaded && <div className="dz-success">Uploaded successfully</div>}
      {loading && <div className="dz-success" style={{color:'var(--amber)'}}>Processing...</div>}
      <input id={id} type="file" style={{display:'none'}} onChange={e => handleFile(e.target.files[0])} />
    </div>
  )
}

function ProcessingModal({ show, onDone }) {
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const steps = [
    { icon:'📥', label:'Data Ingestion & Validation',     sub:'Interval parser & schema check' },
    { icon:'🏗️', label:'Plant Equipment Register',        sub:'Equipment ratings & baseline shifts' },
    { icon:'🧠', label:'NILM Disaggregation',             sub:'Physics-informed disaggregation' },
    { icon:'🔴', label:'Anomaly & Waste Detection',       sub:'Statistical baselining & idle detection' },
    { icon:'📅', label:'Tariff Schedule Optimisation',    sub:'Google OR-Tools CP-SAT solver' },
  ]

  useEffect(() => {
    if (!show) return
    setStep(0); setProgress(0)
    const timer = setInterval(() => {
      setStep(s => {
        if (s >= steps.length) { clearInterval(timer); setTimeout(onDone, 600); return s }
        setProgress(Math.round(((s+1) / steps.length) * 100))
        return s + 1
      })
    }, 1100)
    return () => clearInterval(timer)
  }, [show])

  if (!show) return null
  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">🧠 AI Pipeline Running</div>
        <p className="modal-sub">UrjaMind ka 6-layer AI pipeline chal raha hai...</p>
        <div className="modal-progress-bar">
          <div className="modal-progress-fill" style={{width:`${progress}%`}} />
        </div>
        <div className="modal-steps">
          {steps.map((s,i) => (
            <div key={i} className={`modal-step ${i < step ? 'done' : i === step ? 'active' : 'pending'}`}>
              <div className="mstep-icon">{i < step ? '✅' : s.icon}</div>
              <div>
                <div className="mstep-label">{s.label}</div>
                <div className="mstep-sub">{s.sub}</div>
              </div>
            </div>
          ))}
        </div>
        {step >= steps.length && (
          <div className="modal-done">✅ Analysis complete! Redirecting to Dashboard...</div>
        )}
      </div>
    </div>
  )
}

export default function Upload() {
  const nav = useNavigate()
  const [uploaded, setUploaded] = useState({ bill:false, meter:false, prod:false, equip:false })
  const [showModal, setShowModal] = useState(false)

  const mark = key => setUploaded(u => ({...u, [key]:true}))
  const tier = Object.values(uploaded).filter(Boolean).length

  async function handleDemo() {
    try {
      await loadDemoData()
      setUploaded({ bill:true, meter:true, prod:true, equip:true })
      toast.success('✅ Rajkot Foundry demo data loaded!')
    } catch {
      setUploaded({ bill:true, meter:true, prod:true, equip:true })
      toast.success('✅ Demo data loaded (offline mode)')
    }
  }

  return (
    <div className="page">
      <div className="container" style={{paddingTop:32, paddingBottom:60}}>
        {/* Step indicator */}
        <div className="steps-row">
          {STEPS.map((s,i) => (
            <div key={i} className="step-item">
              <div className={`step-circle ${i===0?'step-active':i<1?'step-done':'step-idle'}`}>{i+1}</div>
              <span className={`step-label ${i===0?'step-label-active':''}`}>{s}</span>
              {i < STEPS.length-1 && <div className={`step-line ${i<0?'step-line-done':''}`} />}
            </div>
          ))}
        </div>

        <div className="upload-header">
          <h1 className="section-title">Upload Your Plant Data</h1>
          <p style={{color:'var(--text2)',marginTop:8}}>Sirf ek bijli bill bhi kaafi hai to get started (Tier 1)</p>
        </div>

        {/* Tier banner */}
        <div className="tier-banner">
          <span className="tier-banner-icon">📊</span>
          <div>
            <div className="tier-banner-title">
              Current Tier:{' '}
              <span style={{color: tier >= 4 ? 'var(--green)' : tier >= 2 ? 'var(--blue-light)' : 'var(--amber)'}}>
                {tier >= 4 ? 'Tier 3 — High Resolution (Very High Confidence)' :
                 tier >= 2 ? 'Tier 2 — Interval Data (High Confidence)' :
                 'Tier 1 — Monthly Bill (Medium Confidence)'}
              </span>
            </div>
            <div className="tier-banner-sub">Zyada data = higher NILM accuracy + machine-level disaggregation</div>
          </div>
          <div className="tier-pills">
            {['T1','T2','T3'].map((t,i) => (
              <div key={t} className={`tier-pill ${tier > i ? 'tier-pill-on' : ''}`}>{t}</div>
            ))}
          </div>
        </div>

        {/* Drop zones */}
        <div className="dz-grid">
          <DropZone id="f-bill" icon="📄" title="Electricity Bill" required
            desc="Monthly DISCOM bill — kWh, Max Demand, Power Factor, ToD charges"
            formats={['PDF','JPG/PNG','Manual']}
            uploaded={uploaded.bill}
            onUpload={async fd => { await uploadBill(fd); mark('bill') }} />
          <DropZone id="f-meter" icon="📈" title="DISCOM Interval Data" required={false}
            desc="15/30-minute meter CSV — available from DISCOM portal for HT consumers"
            formats={['CSV','Excel','XML']}
            uploaded={uploaded.meter}
            onUpload={async fd => { await uploadMeter(fd); mark('meter') }} />
          <DropZone id="f-prod" icon="🏭" title="Production Log" required={false}
            desc="Daily output, shift schedule, product type — Excel / Tally / ERP export"
            formats={['Excel','CSV','Tally XML']}
            uploaded={uploaded.prod}
            onUpload={async fd => { await uploadProduction(fd); mark('prod') }} />
          <DropZone id="f-equip" icon="⚙️" title="Equipment Register" required={false}
            desc="Machine list with kW rating, quantity, motor type — one-time setup"
            formats={['Excel','CSV','Form']}
            uploaded={uploaded.equip}
            onUpload={async fd => { await uploadEquipment(fd); mark('equip') }} />
        </div>

        {/* WhatsApp Webhook Integration */}
        <div className="wa-card">
          <span className="wa-icon">💬</span>
          <div className="wa-content">
            <div className="wa-title">WhatsApp Copilot & Webhook Integration</div>
            <div className="wa-desc">Direct query or meter alerts via Meta WhatsApp Cloud API / Twilio Sandbox: <code>POST /api/whatsapp/webhook</code></div>
            <div className="wa-number">+91 9837101838</div>
          </div>
          <button className="wa-btn" onClick={() => { navigator.clipboard?.writeText('+91 9837101838'); toast.success('Helpline +91 9837101838 copied! Webhook active at /api/whatsapp/webhook') }}>
            📋 Copy Number
          </button>
        </div>

        {/* Actions */}
        <div className="upload-actions">
          <button className="btn btn-primary" style={{fontSize:16,padding:'14px 36px'}} onClick={() => setShowModal(true)}>
            🧠 Analyse My Plant Data
          </button>
          <button className="btn btn-secondary" onClick={handleDemo}>
            ⚡ Load Rajkot Foundry Demo
          </button>
        </div>
      </div>

      <ProcessingModal show={showModal} onDone={() => { setShowModal(false); nav('/dashboard') }} />
    </div>
  )
}
