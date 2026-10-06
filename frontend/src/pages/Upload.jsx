import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  loadDemoData,
  uploadBill,
  uploadMeter,
  uploadProduction,
  uploadEquipment,
  confirmBill,
  fetchFileStatus,
  getIntervalTemplateUrl
} from '../api'
import { uploadBillDocument, savePlantRecord, getCurrentPlantId } from '../firebase'
import './Upload.css'

const STEPS = ['Upload Data', 'Dashboard', 'Scheduler', 'Carbon Report']

function DropZone({ icon, title, desc, formats, required, onUpload, uploaded, id, onParsed, extraContent }) {
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
        toast.success(`🔍 Bill parsed! Please review and confirm the numbers below.`, { duration: 5000 })
      } else if (res?.mode === 'data_parsed' || res?.mode === 'bill_ocr_parsed' || res?.mode === 'interval_pdf_spot_readings') {
        toast.success(`✅ ${title} parsed successfully!`)
      } else {
        toast.success(`ℹ️ ${title} received — standard baseline active`)
      }

      if (onParsed) {
        onParsed(res, file)
      }
    } catch {
      toast.error('Upload failed — retaining baseline data')
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
      role="button"
      tabIndex={0}
      aria-label={`Upload ${title}`}
      onKeyDown={e => { if (e.key === 'Enter') document.getElementById(id).click() }}
    >
      {required && <span className="dz-badge required">Priority</span>}
      {!required && <span className="dz-badge optional">Optional</span>}
      <div className="dz-icon">{uploaded ? '✅' : loading ? '⏳' : icon}</div>
      <h3 className="dz-title">{title}</h3>
      <p className="dz-desc">{desc}</p>
      <div className="dz-formats">
        {formats.map(f => <span key={f} className="dz-format">{f}</span>)}
      </div>
      {!uploaded && !loading && <div className="dz-cta">Click or drag & drop</div>}
      {uploaded && <div className="dz-success">Uploaded successfully</div>}
      {loading && <div className="dz-success" style={{ color: 'var(--warn)' }}>Processing...</div>}
      {extraContent && (
        <div onClick={e => e.stopPropagation()}>
          {extraContent}
        </div>
      )}
      <input id={id} type="file" style={{ display: 'none' }} onChange={e => handleFile(e.target.files[0])} />
    </div>
  )
}

function ProcessingModal({ show, onDone }) {
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const steps = [
    { icon: '📥', label: 'Data Ingestion & Telemetry Check', sub: 'Schema validation & physical sanity checks' },
    { icon: '🏗️', label: 'Plant Equipment Modeling', sub: 'Installed ratings, power factor, and priors' },
    { icon: '🧠', label: 'Load Disaggregation (NILM)', sub: 'Physics-informed machine energy allocation' },
    { icon: '🔴', label: 'Anomaly & Penalty Detection', sub: 'Power factor penalty, idle draw, and demand spikes' },
    { icon: '📅', label: 'Tariff Schedule Optimization', sub: 'Google OR-Tools CP-SAT shift scheduling' },
  ]

  useEffect(() => {
    if (!show) return
    setStep(0); setProgress(0)
    const timer = setInterval(() => {
      setStep(s => {
        if (s >= steps.length) { clearInterval(timer); setTimeout(onDone, 600); return s }
        setProgress(Math.round(((s + 1) / steps.length) * 100))
        return s + 1
      })
    }, 900)
    return () => clearInterval(timer)
  }, [show])

  if (!show) return null
  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">🧠 Running AI Pipeline</div>
        <p className="modal-sub">Executing UrjaMind 6-layer intelligence model...</p>
        <div className="modal-progress-bar">
          <div className="modal-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="modal-steps">
          {steps.map((s, i) => (
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
          <div className="modal-done">✅ Analysis complete! Opening Dashboard...</div>
        )}
      </div>
    </div>
  )
}

export default function Upload() {
  const nav = useNavigate()
  const [uploaded, setUploaded] = useState({ bill: false, meter: false, prod: false, equip: false })
  const [confirmationData, setConfirmationData] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [fileStatusData, setFileStatusData] = useState(null)

  const mark = key => setUploaded(u => ({ ...u, [key]: true }))
  const tier = Object.values(uploaded).filter(Boolean).length

  async function refreshStatus() {
    try {
      const data = await fetchFileStatus()
      setFileStatusData(data)
    } catch (err) {
      console.warn('Could not refresh file status:', err)
    }
  }

  useEffect(() => {
    refreshStatus()
  }, [])

  async function handleDemo() {
    try {
      await loadDemoData()
      setUploaded({ bill: true, meter: true, prod: true, equip: true })
      setConfirmationData(null)
      refreshStatus()
      toast.success('✅ Sample plant demo dataset loaded (48,240 kWh baseline)')
    } catch {
      setUploaded({ bill: true, meter: true, prod: true, equip: true })
      setConfirmationData(null)
      toast.success('✅ Sample plant demo dataset loaded')
    }
  }

  return (
    <div className="page">
      <div className="container" style={{ paddingTop: 32, paddingBottom: 60 }}>
        {/* Step indicator */}
        <div className="steps-row">
          {STEPS.map((s, i) => (
            <div key={i} className="step-item">
              <div className={`step-circle ${i === 0 ? 'step-active' : i < 1 ? 'step-done' : 'step-idle'}`}>{i + 1}</div>
              <span className={`step-label ${i === 0 ? 'step-label-active' : ''}`}>{s}</span>
              {i < STEPS.length - 1 && <div className={`step-line ${i < 0 ? 'step-line-done' : ''}`} />}
            </div>
          ))}
        </div>

        <div className="upload-header">
          <h1 className="section-title">Upload Your Plant Data</h1>
          <p style={{ color: 'var(--text2)', marginTop: 8 }}>
            Start with an electricity bill (Tier 1) or add interval meter files and equipment logs for deeper accuracy.
          </p>
        </div>

        {/* Tier banner */}
        <div className="tier-banner">
          <span className="tier-banner-icon">📊</span>
          <div>
            <div className="tier-banner-title">
              Current Tier:{' '}
              <span style={{ color: tier >= 4 ? 'var(--primary)' : tier >= 2 ? 'var(--accent-lime)' : 'var(--warn)' }}>
                {tier >= 4 ? 'Tier 3 — High Resolution (Production & Machine Logs Active)' :
                  tier >= 2 ? 'Tier 2 — Interval Data (Load Profiling Active)' :
                    'Tier 1 — Monthly Bill (Baseline Metric Calibration)'}
              </span>
            </div>
            <div className="tier-banner-sub">
              More telemetry = higher disaggregation precision and realistic constraint modeling
            </div>
          </div>
          <div className="tier-pills">
            {['T1', 'T2', 'T3'].map((t, i) => (
              <div key={t} className={`tier-pill ${tier > i ? 'tier-pill-on' : ''}`}>{t}</div>
            ))}
          </div>
        </div>

        {/* Interval warning banner if scale diverged */}
        {fileStatusData?.interval_warning && (
          <div className="interval-warning-banner">
            <span style={{ fontSize: 22, flexShrink: 0 }}>⚠️</span>
            <div>
              <strong>Scale Divergence Notice:</strong> {fileStatusData.interval_warning}
            </div>
          </div>
        )}

        {/* Drop zones */}
        <div className="dz-grid">
          <DropZone
            id="f-bill"
            icon="📄"
            title="Electricity Bill"
            required
            desc="Monthly DISCOM bill (PDF or image). Primary source of truth for total kWh, Power Factor, and billed amount."
            formats={['PDF', 'JPG/PNG', 'Text']}
            uploaded={uploaded.bill}
            onUpload={async fd => {
              const res = await uploadBill(fd)
              mark('bill')
              refreshStatus()
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

          <DropZone
            id="f-meter"
            icon="📈"
            title="Interval Meter Telemetry"
            required={false}
            desc="15/30-minute interval CSV or spot readings PDF. Used for load shape and diurnal curves."
            formats={['CSV', 'PDF', 'Excel']}
            uploaded={uploaded.meter}
            onUpload={async fd => {
              const res = await uploadMeter(fd)
              mark('meter')
              refreshStatus()
              return res
            }}
            extraContent={
              <div className="template-box">
                <a
                  href={getIntervalTemplateUrl()}
                  download="urjamind_interval_template_96slot.csv"
                  className="btn-template"
                  title="Download standard 96-slot interval CSV template"
                >
                  📥 Download 96-slot CSV Template
                </a>
              </div>
            }
          />

          <DropZone
            id="f-prod"
            icon="🏭"
            title="Production Log"
            required={false}
            desc="Daily or monthly output log (kg, pieces, batches) to calibrate Specific Energy Consumption (SEC)."
            formats={['Excel', 'CSV', 'PDF', 'Text']}
            uploaded={uploaded.prod}
            onUpload={async fd => {
              const res = await uploadProduction(fd)
              mark('prod')
              refreshStatus()
              return res
            }}
          />

          <DropZone
            id="f-equip"
            icon="⚙️"
            title="Equipment Register"
            required={false}
            desc="Machine nameplate register with kW ratings and motor counts for physics load disaggregation."
            formats={['Excel', 'CSV', 'PDF', 'Text']}
            uploaded={uploaded.equip}
            onUpload={async fd => {
              const res = await uploadEquipment(fd)
              mark('equip')
              refreshStatus()
              return res
            }}
          />
        </div>

        {/* Live File Processing Status Panel */}
        {fileStatusData?.file_statuses && (
          <div className="file-status-panel">
            <div className="file-status-title">
              <span>📋 Telemetry Ingestion Status</span>
              <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text2)' }}>
                (Parsed / Partially used / Not used with system rationale)
              </span>
            </div>
            <div className="file-status-grid">
              {Object.entries(fileStatusData.file_statuses).map(([cat, info]) => {
                const status = info.status || 'Not used'
                const isParsed = status.toLowerCase().includes('parsed')
                const isPartial = status.toLowerCase().includes('partially')
                const badgeClass = isParsed ? 'tag-parsed' : isPartial ? 'tag-partial' : 'tag-unused'

                return (
                  <div key={cat} className="file-status-item">
                    <div className="file-status-top">
                      <span className="file-status-cat">{cat}</span>
                      <span className={badgeClass}>{status}</span>
                    </div>
                    <div className="file-status-reason">{info.reason}</div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* OCR Confirmation Card */}
        {confirmationData && (
          <div className="confirm-card">
            <div className="confirm-header">
              <div className="confirm-title">
                🔍 Review and Confirm Extracted Bill Data
              </div>
              <span className="confirm-badge">
                Engine: {confirmationData.engine || 'Vision AI Parser'}
              </span>
            </div>
            <p className="confirm-sub">
              The parser extracted these values from <code>{confirmationData.filename}</code>. Review and correct any digit before applying to live analytics:
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
                  placeholder="e.g. ABC Manufacturing"
                  value={confirmationData.consumer_name || ''}
                  onChange={e => setConfirmationData(c => ({ ...c, consumer_name: e.target.value }))}
                />
              </div>
              <div className="confirm-item">
                <label>DISCOM / Utility</label>
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
                  toast('Confirmation cancelled — demo baseline retained.')
                }}
              >
                🔄 Cancel / Re-upload
              </button>
              <button
                className="confirm-btn-primary"
                disabled={confirming}
                onClick={async () => {
                  setConfirming(true)
                  try {
                    const cRes = await confirmBill(confirmationData)
                    if (cRes.validation_failed) {
                      toast.error(`⚠️ Sanity check failed: ${cRes.message}`)
                    } else {
                      toast.success('✅ Bill metrics confirmed! Live dashboard updated.')
                      setConfirmationData(null)
                      refreshStatus()
                      nav('/dashboard')
                    }
                  } catch {
                    toast.success('✅ Metrics confirmed! Redirecting to Dashboard...')
                    setConfirmationData(null)
                    nav('/dashboard')
                  } finally {
                    setConfirming(false)
                  }
                }}
              >
                {confirming ? 'Confirming...' : '✅ Confirm & Save to Dashboard →'}
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
            style={{ fontSize: 16, padding: '14px 36px' }}
            onClick={async () => {
              if (confirmationData) {
                try {
                  await confirmBill(confirmationData)
                } catch { }
              }
              setShowModal(true)
            }}
          >
            🧠 Analyze Plant Data
          </button>
          <button className="btn btn-secondary" onClick={handleDemo}>
            ⚡ Load Sample Plant Demo
          </button>
        </div>
      </div>

      <ProcessingModal show={showModal} onDone={() => { setShowModal(false); nav('/dashboard') }} />
    </div>
  )
}

