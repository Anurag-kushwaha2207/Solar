"""Anomaly router — numbers from constants.py"""
from fastapi import APIRouter
from constants import (
    ANOMALY_SAVING_COMPRESSOR_INR, ANOMALY_SAVING_FURNACE_INR,
    ANOMALY_SAVING_PRESS3_INR, ANOMALY_SAVING_PF_INR, TOTAL_ANOMALY_SAVING_INR,
)

router = APIRouter()

ALERTS = [
    {
        "id": 1,
        "machine": "Air Compressor (75 kW)",
        "alert_type": "idle_waste",
        "severity": "high",
        "title": "Idle Compressor — Raat 11 PM se 3 AM",
        "description": (
            "Physics model: 4.2 kW idle draw × ~4h × 22 nights = 370 kWh/month wasted. "
            "Compressor chal raha hai jab production zero hai."
        ),
        "potential_saving_inr": ANOMALY_SAVING_COMPRESSOR_INR,
        "potential_saving_kwh": 370,
        "method": "physics-simulation",
        "confidence": None,
        "action": "Install auto-shutoff timer — one-time cost ₹2,000.",
        "note": "Verify with actual midnight ampere reading before acting.",
    },
    {
        "id": 2,
        "machine": "Induction Furnace (500 kg)",
        "alert_type": "peak_tariff",
        "severity": "medium",
        "title": "Furnace Melting — Peak Tariff Hours 6–10 PM",
        "description": (
            "Melting during 18:00–22:00 at ₹8.20/kWh. "
            "Shifting to 22:00–06:00 (₹4.50/kWh) saves ₹3.70/kWh on same energy."
        ),
        "potential_saving_inr": ANOMALY_SAVING_FURNACE_INR,
        "potential_saving_kwh": 0,
        "method": "tariff-calculation",
        "confidence": None,
        "action": "Use Scheduler tab → Run CP-SAT Optimizer.",
        "note": "Tariff saving only — kWh and CO₂ unchanged.",
    },
    {
        "id": 3,
        "machine": "Hydraulic Press #3",
        "alert_type": "degradation",
        "severity": "medium",
        "title": "Motor Degradation — Press #3 Specific Energy Creep",
        "description": (
            "Physics simulation: specific energy trending +0.3% per day over 6 weeks. "
            "Bearing wear suspected."
        ),
        "potential_saving_inr": ANOMALY_SAVING_PRESS3_INR,
        "potential_saving_kwh": 380,
        "method": "physics-simulation",
        "confidence": None,
        "action": "Schedule bearing inspection. Estimated cost ₹3,500.",
        "note": "Confirm with actual kWh/cycle data logging.",
    },
    {
        "id": 4,
        "machine": "All Motors",
        "alert_type": "pf_drop",
        "severity": "low",
        "title": "Power Factor Drop — Capacitor Bank",
        "description": "Measured PF: 0.870. DISCOM penalty active.",
        "potential_saving_inr": ANOMALY_SAVING_PF_INR,
        "potential_saving_kwh": 0,
        "method": "measured",
        "confidence": None,
        "action": "Capacitor bank re-tuning. Cost ₹8,000–15,000.",
        "note": "PF is from DISCOM meter — this is real measured data.",
    },
]


@router.get("/alerts")
async def get_alerts(plant_id: int = 1, severity: str = None):
    alerts = [a for a in ALERTS if severity is None or a["severity"] == severity]
    return {
        "plant_id": plant_id,
        "total_alerts": len(alerts),
        "total_potential_saving_inr": TOTAL_ANOMALY_SAVING_INR,
        "model": "Physics simulation + measured PF (Phase 1). LSTM-VAE planned Phase 2.",
        "alerts": alerts,
    }


@router.get("/summary")
async def get_summary():
    return {
        "high": 1, "medium": 2, "low": 1,
        "total_saving_inr": TOTAL_ANOMALY_SAVING_INR,
        "note": "Physics simulation — not from trained LSTM-VAE",
    }


@router.post("/resolve/{alert_id}")
async def resolve_alert(alert_id: int):
    return {"status": "resolved", "alert_id": alert_id}
