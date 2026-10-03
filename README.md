# ⚡ UrjaMind — AI Energy Intelligence for Indian SMEs

> **Hardware-free · Physics-Informed · Real Google OR-Tools CP-SAT Optimizer**

UrjaMind helps Indian SMEs reduce industrial electricity bills and ToD peak surcharges using data they already have — electricity bills, DISCOM interval meter data, and production logs. No expensive smart-meter retrofits or IoT hardware required.

---

## 🔗 Live Application

- **Full-Stack App:**
  - Backend: `cd backend && uvicorn main:app --reload` (FastAPI at `http://localhost:8000`)
  - Frontend: `cd frontend && npm run dev` (Vite + React at `http://localhost:5173`)
- **Interactive Prototype:** Open [`urjamind/index.html`](file:///c:/Users/Anurag%20kushwaha/Documents/Solar/urjamind/index.html) in your browser.

---

## 🔍 Ground Reality & What Works Today (Phase 1 Prototype vs Phase 2 Roadmap)

| Component | Status in Repo | Implementation Reality & Transparency |
|---|---|---|
| **Tariff Scheduler** | ✅ **REAL** | Google OR-Tools 9.x CP-SAT solver. Finds global optimal schedule in <0.3s respecting 250 kVA Max Demand. Monthly saving: **₹47,500/month (16.5%)**. |
| **Comparative Heuristic** | ✅ **REAL** | Live Greedy benchmark solver running independently alongside CP-SAT. |
| **Carbon Accounting** | ✅ **REAL** | Verified CEA Western Grid emission factor (0.716 kgCO₂e/kWh), Scope 1 diesel logs, and cryptographically verified SHA-256 payload digest. |
| **Data Ingestion & OCR** | ✅ **REAL** | Digital PDF parser (PyMuPDF) + Scanned Bill Photo OCR (Claude Vision) with strict physical sanity bounds (`kWh > 0`, `0.5 ≤ PF ≤ 1.0`, `amount > 0`) and user confirmation UI. |
| **Security & Auth** | ✅ **REAL** | Firebase Auth token verification, production token locking (401 for demo tokens in `ENVIRONMENT=production`), Twilio/Meta HMAC-SHA256 signature verification, dynamic CORS. |
| **Machine NILM** | 🔬 Phase 1 | Physics-informed equipment register breakdown (sums strictly to 48,240 kWh). Neural Seq2Point/Transformer training on real IMDELD/HIPE datasets is Phase 2 (post-Oct 11). |
| **Anomaly Detection** | 🔬 Phase 1 | Physics rules (e.g. 4.2 kW compressor idle draw, low PF 0.870) totaling ₹12,400/month without double-counting. Deep LSTM-VAE is Phase 2. |
| **Copilot** | 🔬 Phase 1 | Multi-tool agentic engine (grounded in tool outputs, strictly executing verified analytical solvers). |
| **Digital Twin & Forecasting** | 🔬 Phase 2 | LightGBM baseline forecasting and digital twin models will be trained during the hackathon prototype phase (from Oct 11 onwards). |

---

## 📅 Scheduler Results (Verified with Google OR-Tools CP-SAT)

```text
Contract Max Demand:       250 kVA (Gujarat PGVCL ToD tariff)
Baseline Daily Cost:       ₹11,499.05 / day
Optimal Daily Cost:        ₹9,599.05 / day
Daily Cost Reduction:      ₹1,900.00 / day (16.5% reduction)
Working Days per Month:    25 days
Monthly Saving:            ₹47,500.00 / month

Key Job Shifts:
  • Furnace Melt #1 (160 kW, 11 slots): 06:00 (normal ₹6.20) → 00:00 (off-peak ₹4.50)  — saves ₹748/day
  • Furnace Melt #2 (160 kW, 11 slots): 18:00 (peak ₹8.20)   → 05:00 (off-peak ₹4.50)  — saves ₹1,152/day
  • Furnace Safety Hold (40 kW, 4 slots): Fixed at 09:00 (regulatory lock, zero drift)
  • Hydraulic Press & Fettling: Scheduled within 8 AM–5 PM shift within MD headroom
  • Compressor Productive Run: Scheduled during low-tariff working hours
```

### Energy Balance Sanity Check (Monthly Total = 48,240 kWh)
- Furnace Melts (2 × 440 kWh) + Hold (40 kWh) = 920 kWh/day
- Air Compressor (productive run) = 356 kWh/day
- Hydraulic Pressing = 248 kWh/day
- Fettling Operations = 192 kWh/day
- Total schedulable = ~1,716 kWh/day
- HVAC base load = ~213 kWh/day
- **Total daily plant draw = ~1,929 kWh/day × 25 days ≈ 48,225 kWh (matches 48,240 kWh DISCOM bill within <0.1%)**

---

## 🌿 Carbon Accounting & Audit Trail

- **Scope 2:** `48,240 kWh × 0.716 kgCO₂e/kWh ÷ 1000 = 34.54 tCO₂e` (CEA v18 Western Regional Grid)
- **Scope 1:** Diesel generator logs = 3.20 tCO₂e
- **Total Sep 2026 Emissions:** 37.74 tCO₂e
- **Cryptographic Audit Digest:** SHA-256 hash computed directly on official reporting payload (`3ce423485e084eb1...4fd437d0`) for buyer disclosure and CBAM readiness.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.11+, FastAPI, Google OR-Tools (`ortools==9.15.6755`), NumPy, Pandas, Pydantic
- **Frontend:** React 18, Vite 5, Recharts, React Hot Toast, Vanilla CSS tokens
- **Optimization:** Mixed-Integer Linear Programming / Constraint Programming (CP-SAT)
- **Standards:** GHG Protocol Corporate Standard, CEA CO₂ Baseline v18

---

*UrjaMind — Indian SME Industrial Energy Optimization*
