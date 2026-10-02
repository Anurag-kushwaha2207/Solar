# UrjaMind — AI Energy Intelligence for Indian SMEs

> **Hardware-free · Physics Simulation (Phase 1) · Real CP-SAT Optimizer**

UrjaMind helps Indian SMEs reduce energy costs by optimizing ToD scheduling — using only data they already have (electricity bills, DISCOM meter data, production logs). No sensors, no expensive IoT deployment.

---

## Live Demo

**Full-stack app:** `cd frontend && npm run dev` + `cd backend && uvicorn main:app`  
**Static prototype:** Open `urjamind/index.html` in browser.

---

## What is Actually Working (Phase 1)

| Feature | Status | Honest Description |
|---------|--------|--------------------|
| Data Upload | ✅ Working | File accepted. Bill OCR: **Phase 2** (planned) |
| Machine Breakdown (NILM) | ⚠ Simulated | Physics rules from equipment register. ML model: **Phase 2** |
| Anomaly Alerts | ⚠ Simulated | Physics-based rules (4.2 kW idle × 4h × 22 nights). LSTM-VAE: **Phase 2** |
| **Tariff Scheduler** | ✅ **REAL** | OR-Tools CP-SAT 9.x. OPTIMAL in 0.3s. Saving: Rs.40,560/month (17.6%) |
| Carbon Report | ✅ Real calculation | 48,240 kWh × 0.716 kg/kWh = 34.54 tCO₂e (CEA 2023-24 Western Grid) |
| Copilot | ⚠ Rule-based | Intent matching + constants.py. LLM with RAG: **Phase 2** |
| Bill OCR | ❌ Not yet | Always returns demo values. PaddleOCR integration: **Phase 2** |

---

## Scheduler Result (Verified)

```
Current schedule (daily):  Rs.8,884
CP-SAT optimal (daily):    Rs.7,324
Saving per working day:    Rs.1,560
Working days/month:        26
Monthly saving:            Rs.40,560  (17.6%)

What changed:
  Furnace Melt #1: 6AM (Rs.6.20) → midnight (Rs.4.50)  — saves Rs.680/day
  Furnace Melt #2: 6PM (Rs.8.20) → 3PM  (Rs.6.20)     — saves Rs.880/day
  Press + Fettling: unchanged (no off-peak window available, deadline 5PM)
  Safety Hold: fixed 9AM (regulatory, cannot move)
```

Daily energy consistency check:
- Furnace (21 slots × 160 kW × 0.25h): 840 kWh × 26 days = 21,840 kWh ≈ 21,400 ✓
- Compressor (18 slots × 75 kW × 0.25h): 338 kWh × 26 days = 8,775 kWh ≈ 8,900 ✓
- Press (14 slots × 66 kW × 0.25h): 231 kWh × 26 days = 6,006 kWh ≈ 6,200 ✓
- Fettling (20 slots × 36 kW × 0.25h): 180 kWh × 26 days = 4,680 kWh ≈ 4,800 ✓
- HVAC base: 18 kW × 12.8h/day × 30 days = 6,912 kWh ≈ 6,940 ✓
- **Total: ~48,213 kWh ≈ 48,240 kWh** ✓ (consistent with bill)

---

## 6-Layer Pipeline (Current Status)

```
Bill PDF / DISCOM CSV / Production Log
        ↓
[Layer 1] Data Ingestion — file accepted; OCR parsing PLANNED Phase 2
        ↓
[Layer 2] Digital Twin — physics simulation (Phase 1); SimPy PLANNED Phase 2
        ↓
[Layer 3] NILM Disaggregation — physics rules (Phase 1); Seq2Point/IMDELD PLANNED Phase 2
        ↓
[Layer 4] Anomaly Detection — rule-based physics (Phase 1); LSTM-VAE PLANNED Phase 2
        ↓
[Layer 5] Tariff Scheduler — REAL CP-SAT (OR-Tools 9.x) ✅; PPO RL PLANNED Phase 2
        ↓
[Layer 6] Carbon (real CEA calc ✅) + Copilot (rule-based; LLM PLANNED Phase 2)
```

---

## Numbers — All From Single Source of Truth

All numbers derive from `backend/constants.py` — no inconsistencies across endpoints:

| Metric | Value | Source |
|--------|-------|--------|
| Total kWh Sep 2026 | 48,240 kWh | DISCOM meter |
| Total bill | Rs.2,96,500 | DISCOM bill |
| Blended rate | Rs.6.08/kWh | 293,300 ÷ 48,240 |
| Scope 2 emissions | 34.54 tCO₂e | 48,240 × 0.716 kg/kWh ÷ 1000 |
| Emission factor | 0.716 kg/kWh | CEA v18 Western Regional Grid 2023-24 |
| Scheduler saving | Rs.40,560/month | CP-SAT OPTIMAL (real solver) |
| Anomaly savings | Rs.22,600/month | Physics simulation (labelled as such) |

---

## Tech Stack (Phase 1 — What's Actually Installed)

| Component | Status | Package |
|-----------|--------|---------|
| API backend | ✅ | FastAPI 0.111, Uvicorn |
| **Scheduler** | ✅ **REAL** | `ortools==9.15.6755` |
| Frontend | ✅ | React + Vite |
| Data processing | ✅ | pandas, numpy, scipy |
| Analytics | ✅ | scikit-learn (baseline regression) |
| NILM model | ❌ Phase 2 | PyTorch (not in requirements yet) |
| Bill OCR | ❌ Phase 2 | PaddleOCR (not installed) |
| LLM Copilot | ❌ Phase 2 | Gemini API / LangChain (not integrated) |
| PPO RL | ❌ Phase 2 | stable-baselines3 (not installed) |

---

## Target Industries

- Foundries (Rajkot, Coimbatore)
- Textile mills (Ludhiana, Surat)
- Ceramics (Morbi)
- Brick kilns
- Chemical / food processing SMEs

---

*Built for Hackathon Submission · October 2026*  
*Honesty policy: Every claim is labelled Phase 1 (working) or Phase 2 (planned).*
