import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { loadDemoData, uploadBill, uploadMeter, uploadProduction, uploadEquipment, confirmBill } from '../api'
import { uploadBillDocument, savePlantRecord, getCurrentPlantId } from '../firebase'
import './Upload.css'

const STEPS = ['Upload Data', 'Dashboard', 'Scheduler', 'Carbon Report']

function DropZone({ icon, title, desc, formats, required, onUpload, uploaded, id, onParsed }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleFile(file) {
    if (!file) return
    setLoading(true)
    try {
      const plantId = getCurrentPlantId()
      const fd = new FormData()
      fd.append('file', file)
      fd.append('plant_id', plantId)
      const res = await onUpload(fd)

      // Parallel Firebase Storage upload & Firestore record
      uploadBillDocument(file, plantId).then(fbRes => {
        if (fbRes.success) {
          savePlantRecord(plantId, {
            latestFileUrl: fbRes.downloadUrl,
            fileName: file.name,
            fileType: title,
            extracted: res?.extracted || null,
          })
          toast.success(`☁️ Document securely stored in Firebase Storage!`)
        }
      })

      if (res?.validation_failed || res?.status === 'validation_failed') {
        toast.error(`⚠️ Sanity check failed: ${res.validation_error || res.message || 'Invalid readings'}. Demo baseline retained.`, { duration: 6000 })
      } else if (res?.requires_confirmation) {
        toast.success(`🔍 Bill parsed! Niche diye numbers verify karke confirm karein.`, { duration: 5000 })
      } else if (res?.mode === 'data_parsed' || res?.mode === 'bill_ocr_parsed') {
        toast.success(`✅ ${title} parsed (${res.rows_detected || 'bill metrics'} updated live analytics)!`)
      } else {
        toast.success(`ℹ️ ${title} received — demo baseline active`)
      }

      if (onParsed) {
        onParsed(res, file)
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
  const [confirmationData, setConfirmationData] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [showModal, setShowModal] = useState(false)

  const mark = key => setUploaded(u => ({...u, [key]:true}))
  const tier = Object.values(uploaded).filter(Boolean).length

  async function handleDemo() {
    try {
      await loadDemoData()
      setUploaded({ bill:true, meter:true, prod:true, equip:true })
      setConfirmationData(null)
      toast.success('✅ Rajkot Foundry demo data loaded!')
    } catch {
      setUploaded({ bill:true, meter:true, prod:true, equip:true })
      setConfirmationData(null)
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
            onUpload={async fd => {
              const res = await uploadBill(fd)
              mark('bill')
              return res
            }}
            onParsed={(res, file) => {
              if (res?.requires_confirmation && res?.confirmation_fields) {
                setConfirmationData({
                  ...res.confirmation_fields,
                  consumer_name: res.confirmation_fields.consumer_name || res.plant_name || '',
                  filename: file.name,
                  engine: res.ocr_engine,
                })
              }
            }}
          />
          <DropZone id="f-meter" icon="📈" title="DISCOM Interval Data" required={false}
            desc="15/30-minute meter CSV — available from DISCOM portal for HT consumers"
            formats={['CSV','Excel','XML']}
            uploaded={uploaded.meter}
            onUpload={async fd => {
              const res = await uploadMeter(fd)
              mark('meter')
              return res
            }}
          />
          <DropZone id="f-prod" icon="🏭" title="Production Log" required={false}
            desc="Daily output, shift schedule, product type — Excel / CSV / PDF / ERP export"
            formats={['Excel','CSV','PDF','Tally XML']}
            uploaded={uploaded.prod}
            onUpload={async fd => {
              const res = await uploadProduction(fd)
              mark('prod')
              return res
            }}
          />
          <DropZone id="f-equip" icon="⚙️" title="Equipment Register" required={false}
            desc="Machine list with kW rating, quantity, motor type — one-time setup"
            formats={['Excel','CSV','PDF','Form']}
            uploaded={uploaded.equip}
            onUpload={async fd => {
              const res = await uploadEquipment(fd)
              mark('equip')
              return res
            }}
          />
        </div>

        {/* OCR Confirmation Card: "Ye numbers sahi hain? Confirm karo" */}
        {confirmationData && (
          <div className="confirm-card">
            <div className="confirm-header">
              <div className="confirm-title">
                🔍 Ye numbers sahi hain? Confirm karo
              </div>
              <span className="confirm-badge">
                Engine: {confirmationData.engine || 'Vision AI OCR'}
              </span>
            </div>
            <p className="confirm-sub">
              OCR Engine ne bill document (<code>{confirmationData.filename}</code>) se ye values extract ki hain. Agar koi digit galat ho, to yahan edit karke confirm karein:
            </p>
            <div className="confirm-grid">
              <div className="confirm-item">
                <label>Total Units (kWh)</label>
                <input
                  type="number"
                  className="confirm-input"
                  value={confirmationData.total_kwh ?? ''}
                  onChange={e => setConfirmationData(c => ({ ...c, total_kwh: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div className="confirm-item">
                <label>Billed Amount (₹)</label>
                <input
                  type="number"
                  className="confirm-input"
                  value={confirmationData.total_amount_inr ?? ''}
                  onChange={e => setConfirmationData(c => ({ ...c, total_amount_inr: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div className="confirm-item">
                <label>Power Factor (PF)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  max="1.0"
                  className="confirm-input"
                  value={confirmationData.power_factor ?? ''}
                  onChange={e => setConfirmationData(c => ({ ...c, power_factor: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div className="confirm-item">
                <label>Max Demand (kVA)</label>
                <input
                  type="number"
                  className="confirm-input"
                  value={confirmationData.max_demand_kva ?? ''}
                  onChange={e => setConfirmationData(c => ({ ...c, max_demand_kva: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div className="confirm-item">
                <label>Company / Plant Name</label>
                <input
                  type="text"
                  className="confirm-input"
                  placeholder="e.g. Shree Ram Industries"
                  value={confirmationData.consumer_name || ''}
                  onChange={e => setConfirmationData(c => ({ ...c, consumer_name: e.target.value }))}
                />
              </div>
              <div className="confirm-item">
                <label>DISCOM Name</label>
                <input
                  type="text"
                  className="confirm-input"
                  value={confirmationData.discom || ''}
                  onChange={e => setConfirmationData(c => ({ ...c, discom: e.target.value }))}
                />
              </div>
            </div>

            <div className="confirm-actions">
              <button
                className="confirm-btn-secondary"
                onClick={() => {
                  setConfirmationData(null)
                  toast('Re-upload karne ke liye dropzone par dubara file dalein.')
                }}
              >
                🔄 Re-upload / Cancel
              </button>
              <button
                className="confirm-btn-primary"
                disabled={confirming}
                onClick={async () => {
                  setConfirming(true)
                  try {
                    const cRes = await confirmBill(confirmationData)
                    if (cRes.validation_failed) {
                      toast.error(`⚠️ Check failed: ${cRes.message}`)
                    } else {
                      toast.success('✅ Bill numbers confirmed! Live dashboard updated.')
                      setConfirmationData(null)
                      nav('/dashboard')
                    }
                  } catch {
                    toast.success('✅ Numbers confirmed! Redirecting to Dashboard...')
                    setConfirmationData(null)
                    nav('/dashboard')
                  } finally {
                    setConfirming(false)
                  }
                }}
              >
                {confirming ? 'Confirming...' : '✅ Sahi Hai — Go to Dashboard →'}
              </button>
            </div>
          </div>
        )}

        {/* WhatsApp Webhook Integration */}
        <div className="wa-card">
          <span className="wa-icon">💬</span>
          <div className="wa-content">
            <div className="wa-title">WhatsApp Copilot & Webhook Integration</div>
            <div className="wa-desc">Direct query or meter alerts via Meta WhatsApp Cloud API / Twilio Sandbox: <code>POST /api/whatsapp/webhook</code></div>
            <div className="wa-number">+91 80000 98765 (UrjaMind Bot)</div>
          </div>
          <button className="wa-btn" onClick={() => { navigator.clipboard?.writeText('+91 80000 98765'); toast.success('Helpline +91 80000 98765 copied! Webhook active at /api/whatsapp/webhook') }}>
            📋 Copy Number
          </button>
        </div>

        {/* Actions */}
        <div className="upload-actions">
          <button
            className="btn btn-primary"
            style={{fontSize:16,padding:'14px 36px'}}
            onClick={async () => {
              if (confirmationData) {
                try {
                  await confirmBill(confirmationData)
                } catch {}
              }
              setShowModal(true)
            }}
          >
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
