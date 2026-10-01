import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── Dashboard ──────────────────────────────────────────────────────────────
export const fetchKPIs         = ()      => api.get('/dashboard/kpis').then(r => r.data)
export const fetchLoadProfile  = (days=1) => api.get(`/dashboard/load-profile?days=${days}`).then(r => r.data)
export const fetchMachines     = ()      => api.get('/dashboard/machine-breakdown').then(r => r.data)
export const fetchBaseline     = ()      => api.get('/dashboard/baseline-trend').then(r => r.data)
export const fetchTariff       = ()      => api.get('/dashboard/tariff').then(r => r.data)

// ── NILM ───────────────────────────────────────────────────────────────────
export const fetchNILM         = ()      => api.get('/nilm/disaggregate').then(r => r.data)
export const fetchAblation     = ()      => api.get('/nilm/resolution-ablation').then(r => r.data)

// ── Anomaly ────────────────────────────────────────────────────────────────
export const fetchAnomalies    = ()      => api.get('/anomaly/alerts').then(r => r.data)
export const resolveAnomaly    = (id)    => api.post(`/anomaly/resolve/${id}`).then(r => r.data)

// ── Scheduler ──────────────────────────────────────────────────────────────
export const fetchJobs         = ()      => api.get('/scheduler/jobs').then(r => r.data)
export const optimizeSchedule  = (body)  => api.post('/scheduler/optimize', body).then(r => r.data)

// ── Carbon ─────────────────────────────────────────────────────────────────
export const fetchCarbonReport = ()      => api.get('/carbon/report').then(r => r.data)
export const fetchIntensity    = ()      => api.get('/carbon/intensity-trend').then(r => r.data)

// ── Copilot ────────────────────────────────────────────────────────────────
export const chatWithCopilot   = (msg)   => api.post('/copilot/chat', { message: msg }).then(r => r.data)
export const fetchQuickQs      = ()      => api.get('/copilot/quick-questions').then(r => r.data)

// ── Ingestion ──────────────────────────────────────────────────────────────
export const loadDemoData      = ()      => api.post('/ingest/load-demo').then(r => r.data)
export const uploadBill        = (fd)    => api.post('/ingest/upload-bill', fd, { headers: { 'Content-Type': 'multipart/form-data' }}).then(r => r.data)
export const uploadMeter       = (fd)    => api.post('/ingest/upload-meter-data', fd, { headers: { 'Content-Type': 'multipart/form-data' }}).then(r => r.data)
export const uploadProduction  = (fd)    => api.post('/ingest/upload-production', fd, { headers: { 'Content-Type': 'multipart/form-data' }}).then(r => r.data)
export const uploadEquipment   = (fd)    => api.post('/ingest/upload-equipment', fd, { headers: { 'Content-Type': 'multipart/form-data' }}).then(r => r.data)

export default api
