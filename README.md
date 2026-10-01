# ⚡ UrjaMind — AI Energy Intelligence for Indian SMEs

> **Hardware-free · AI-driven · Zero data scientists required**

UrjaMind helps Indian SMEs reduce energy costs by **15–25%** using only data they already have — electricity bills, DISCOM meter data, and production logs. No sensors, no expensive IoT deployment.

---

## 🔗 Live Demo

Open `urjamind/index.html` in your browser to explore the full prototype.

| Screen | File | Description |
|--------|------|-------------|
| 🏠 Landing Page | `urjamind/index.html` | Problem, pipeline overview, data tiers |
| 📥 Data Upload | `urjamind/upload.html` | Upload bill, meter CSV, production log |
| 📊 Energy Dashboard | `urjamind/dashboard.html` | NILM disaggregation, anomaly alerts, LLM copilot |
| 📅 Scheduler | `urjamind/scheduler.html` | ToD tariff optimiser, Gantt chart |
| 🌿 Carbon Report | `urjamind/carbon.html` | GHG Protocol Scope 1 & 2, M&V table |

---

## 🧠 The 6-Layer AI Pipeline

```
Bill PDF / DISCOM CSV / WhatsApp / Production Log
        ↓
[Layer 1] Data Ingestion — OCR, schema validation
        ↓
[Layer 2] Plant Digital Twin — SimPy simulation, synthetic labeled data
        ↓
[Layer 3] NILM Disaggregation — Transformer/Seq2Point, physical constraints
        ↓
[Layer 4] Anomaly & Waste Detection — LSTM-VAE, drift detection
        ↓
[Layer 5] Tariff-Aware Scheduler — CP-SAT + PPO RL
        ↓
[Layer 6] Carbon Module + LLM Copilot — GHG Protocol + Hindi/Hinglish RAG
```

---

## 💡 Problem Being Solved

Indian SMEs (foundry, textile, ceramics, brick kiln, etc.) face 4 critical gaps:

1. **Visibility Gap** — Bill sirf ek total number; machine-level breakdown nahi
2. **Diagnosis Gap** — Bill kyun badha? Koi tool nahi
3. **Action Gap** — ToD tariff ka fayda kaise lein? Koi scheduler nahi
4. **Proof Gap** — Export buyer carbon data maang raha hai, GHG report nahi hai

---

## 🎯 Key Features

- **Zero Hardware** — Existing bill + DISCOM data kaafi hai
- **Data-Tier Adaptive** — Monthly bill (Tier 1) se high-res data (Tier 3) tak graceful degradation
- **Digital Twin** — SimPy-based synthetic labeled data for NILM training
- **Vernacular Copilot** — Hindi/Hinglish LLM with tool-grounded answers (no hallucination)
- **M&V Verified** — IPMVP-style measurement & verification of every saving claim
- **GHG Protocol** — Scope 1 & 2 auto-report with full audit trail

---

## 📊 Target Impact (Simulation)

| Metric | Value |
|--------|-------|
| Energy cost reduction | 15–25% |
| Avg. annual saving / SME unit | ₹1.2L+ |
| Carbon avoided | ~14 tCO₂e/year/unit |
| Hardware required | **Zero** |

> *Numbers based on public dataset simulation (HIPE, IMDELD) + synthetic digital twin. Actual savings to be verified on pilot plants.*

---

## 🛠️ Tech Stack

| Layer | Tech |
|-------|------|
| OCR / Ingestion | PaddleOCR, Pydantic, FastAPI |
| Digital Twin | SimPy, NumPy |
| Disaggregation (NILM) | PyTorch Transformer, Seq2Point CNN |
| Anomaly Detection | LSTM-VAE, Isolation Forest |
| Scheduler | OR-Tools CP-SAT, Stable-Baselines3 PPO |
| Baseline Model | LightGBM + SHAP |
| Carbon Module | GHG Protocol, CEA emission factors |
| LLM Copilot | LangChain + RAG + tool-calling guardrails |
| Frontend | React / Streamlit |
| Database | PostgreSQL + TimescaleDB |

---

## 🏭 Target Industries

- Foundries (Rajkot, Coimbatore)
- Textile mills (Ludhiana, Surat)
- Ceramics (Morbi)
- Brick kilns
- Chemical / food processing SMEs

---

*Built for Hackathon Submission · October 2026*
