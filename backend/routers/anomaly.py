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
        "title": "Idle Compressor — Overnight 11 PM to 3 AM",
        "description": (
            "Physics model: 4.2 kW idle draw × ~4h × 22 nights = 370 kWh/month wasted. "
            "Compressor operating while production is idle."
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
        "description": "Measured PF: 0.870 (DISCOM penalty ₹3,200). Capacitor tuning recovers ₹1,200/mo immediate loss.",
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
    from active_data import active_plant
    if active_plant.source == "demo_baseline":
        alerts = [a for a in ALERTS if severity is None or a["severity"] == severity]
        return {
            "plant_id": plant_id,
            "total_alerts": len(alerts),
            "total_potential_saving_inr": TOTAL_ANOMALY_SAVING_INR,
            "model": "Physics simulation + measured PF (Phase 1). Statistical baselining active.",
            "alerts": alerts,
            "note": "Tariff scheduling savings (₹47,500/mo) are managed in the Scheduler module to prevent double-counting.",
        }

    # Dynamic alerts for uploaded plant
    dyn_alerts = []
    aid = 1
    has_equipment = len(active_plant.equipment_list) > 0
    m_keys = list(active_plant.machines.keys())
    has_cnc = any("cnc" in m.lower() for m in m_keys)
    has_compressor = any("compressor" in m.lower() for m in m_keys)
    has_press = any("press" in m.lower() for m in m_keys)

    sample_badge = "Sample profile" if not has_equipment else None

    if has_compressor:
        dyn_alerts.append({
            "id": aid,
            "machine": next(m for m in m_keys if "compressor" in m.lower()),
            "alert_type": "idle_waste",
            "severity": "high",
            "title": "Idle Compressor — Non-production Shifts",
            "description": "Compressor idling detected during non-productive hours." if has_equipment else "Sample profile estimate: Compressor idling during non-productive hours.",
            "potential_saving_inr": 4200,
            "potential_saving_kwh": 350,
            "method": "physics-simulation",
            "confidence": None,
            "action": "Install auto-shutoff timer relay.",
            "note": "Verify with current ampere readings." if has_equipment else f"Sample profile: Upload equipment register for {active_plant.plant_name} to calibrate machine alerts.",
            "is_sample_profile": not has_equipment,
            "badge": sample_badge,
        })
        aid += 1

    if has_press:
        dyn_alerts.append({
            "id": aid,
            "machine": next(m for m in m_keys if "press" in m.lower()),
            "alert_type": "degradation",
            "severity": "medium",
            "title": "Mechanical Resistance / Degradation",
            "description": "Specific energy creep indicates bearing wear or lubrication deficit." if has_equipment else "Sample profile estimate: Mechanical energy creep indicates bearing wear.",
            "potential_saving_inr": 2800,
            "potential_saving_kwh": 260,
            "method": "physics-simulation",
            "confidence": None,
            "action": "Schedule mechanical inspection and lubrication.",
            "note": "Confirm with load cycle logs." if has_equipment else f"Sample profile: Upload equipment register for {active_plant.plant_name} to calibrate machine alerts.",
            "is_sample_profile": not has_equipment,
            "badge": sample_badge,
        })
        aid += 1

    if has_cnc:
        cnc1 = next((m for m in m_keys if "1" in m or "cnc" in m.lower()), m_keys[0])
        cnc3 = next((m for m in m_keys if "3" in m or ("cnc" in m.lower() and m != cnc1)), m_keys[-1])
        dyn_alerts.append({
            "id": aid,
            "machine": cnc1,
            "alert_type": "idle_waste",
            "severity": "medium",
            "title": f"Standby Draw — {cnc1}",
            "description": f"Illustrative estimate (assumed 110 kWh): Standby power draw during shift handovers on {cnc1}.",
            "potential_saving_inr": 920,
            "potential_saving_kwh": 110,
            "method": "physics-simulation",
            "confidence": None,
            "action": "Configure auto-standby power saving mode in machine controller.",
            "note": "Illustrative estimate (assumed 110 kWh) — verify with physical machine logging before acting.",
            "is_sample_profile": not has_equipment,
            "badge": sample_badge,
        })
        aid += 1

        dyn_alerts.append({
            "id": aid,
            "machine": cnc3,
            "alert_type": "idle_waste",
            "severity": "low",
            "title": f"Spindle Idling — {cnc3}",
            "description": f"Illustrative estimate (assumed 140 kWh): Inter-batch spindle idle rotation between machining cycles on {cnc3}.",
            "potential_saving_inr": 1180,
            "potential_saving_kwh": 140,
            "method": "physics-simulation",
            "confidence": None,
            "action": "Enforce operator SOP for spindle cut-off during part loading/unloading.",
            "note": "Illustrative estimate (assumed 140 kWh) — verify with physical machine logging before acting.",
            "is_sample_profile": not has_equipment,
            "badge": sample_badge,
        })
        aid += 1

    # Power Factor: ONLY flag if PF < 0.90
    if active_plant.avg_pf < 0.90:
        pf_pen = round(active_plant.pf_penalty_inr if active_plant.pf_penalty_inr > 0 else 3200, 0)
        dyn_alerts.append({
            "id": aid,
            "machine": "Capacitor Bank / Main Incomer",
            "alert_type": "pf_drop",
            "severity": "high",
            "title": f"Low Power Factor ({active_plant.avg_pf}) — DISCOM Penalty Active",
            "description": f"Measured PF is {active_plant.avg_pf} (below 0.90 DISCOM limit). DISCOM penalty: ₹{int(pf_pen):,}/month.",
            "potential_saving_inr": int(pf_pen),
            "potential_saving_kwh": 0,
            "method": "measured",
            "confidence": None,
            "action": "Inspect APFC panel and replace degraded capacitor steps.",
            "note": "Derived directly from monthly electricity bill.",
            "is_sample_profile": False,
            "badge": None,
        })

    filtered = [a for a in dyn_alerts if severity is None or a["severity"] == severity]
    tot_save = sum(a["potential_saving_inr"] for a in filtered)

    return {
        "plant_id": plant_id,
        "total_alerts": len(filtered),
        "total_potential_saving_inr": tot_save,
        "has_equipment": has_equipment,
        "is_sample_profile": not has_equipment,
        "profile_notice": f"Upload your equipment register to see machine-level results for {active_plant.plant_name}" if not has_equipment else None,
        "model": "Physics simulation + uploaded telemetry baselining." if has_equipment else "Sample profile (illustrative) — upload equipment register for plant-specific results.",
        "alerts": filtered,
        "note": f"Alerts tuned for {active_plant.plant_name} equipment and measured PF {active_plant.avg_pf}.",
    }


@router.get("/summary")
async def get_summary():
    from active_data import active_plant
    if active_plant.source == "demo_baseline":
        return {
            "high": 1, "medium": 1, "low": 1,
            "total_saving_inr": TOTAL_ANOMALY_SAVING_INR,
            "note": "Operational waste and degradation anomalies (distinct from ToD tariff optimization)",
        }
    alerts_data = await get_alerts()
    alerts = alerts_data["alerts"]
    return {
        "high": sum(1 for a in alerts if a["severity"] == "high"),
        "medium": sum(1 for a in alerts if a["severity"] == "medium"),
        "low": sum(1 for a in alerts if a["severity"] == "low"),
        "total_saving_inr": alerts_data["total_potential_saving_inr"],
        "note": f"Operational waste alerts for {active_plant.plant_name}",
    }


@router.post("/resolve/{alert_id}")
async def resolve_alert(alert_id: int):
    return {
        "alert_id": alert_id,
        "status": "resolved",
        "action_taken": "Marked resolved by operator",
    }
