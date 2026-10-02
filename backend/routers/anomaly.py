"""Anomaly router — operational anomalies only (no double counting with ToD scheduling)"""
from fastapi import APIRouter
from constants import (
    ANOMALY_SAVING_COMPRESSOR_INR,
    ANOMALY_SAVING_PRESS3_INR,
    ANOMALY_SAVING_PF_INR,
    TOTAL_ANOMALY_SAVING_INR,
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
        "id": 3,
        "machine": "All Motors",
        "alert_type": "pf_drop",
        "severity": "low",
        "title": "Power Factor Drop — Capacitor Bank",
        "description": "Measured PF: 0.870. DISCOM penalty active (target >= 0.90).",
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
        "model": "Physics simulation + measured PF (Phase 1). Statistical baselining active.",
        "alerts": alerts,
        "note": "Tariff scheduling savings (₹47,500/mo) are managed in the Scheduler module to prevent double-counting.",
    }


@router.get("/summary")
async def get_summary():
    return {
        "high": 1, "medium": 1, "low": 1,
        "total_saving_inr": TOTAL_ANOMALY_SAVING_INR,
        "note": "Operational waste and degradation anomalies (distinct from ToD tariff optimization)",
    }


@router.post("/resolve/{alert_id}")
async def resolve_alert(alert_id: int):
    return {
        "alert_id": alert_id,
        "status": "resolved",
        "action_taken": "Marked resolved by operator",
    }
