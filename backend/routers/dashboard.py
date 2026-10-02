"""
Dashboard router — all numbers from constants.py (single source of truth)
"""
from fastapi import APIRouter, Query
from constants import (
    PLANT_NAME, REPORT_MONTH, MONTHS_6,
    SEP_TOTAL_KWH, SEP_TOTAL_KVAH, SEP_MAX_DEMAND_KVA,
    SEP_AVG_PF, SEP_PF_PENALTY_INR, SEP_MD_PENALTY_INR,
    SEP_TOTAL_AMOUNT_INR, SEP_TOD_PEAK_KWH, SEP_TOD_OFFPEAK_KWH,
    SEP_PRODUCTION_KG, BASELINE_SEC_ENERGY, SEP_SEC_ENERGY, SEP_DEVIATION_PCT,
    MACHINE_KWH, TOTAL_ANOMALY_SAVING_INR,
    TOD_OFF_PEAK_RATE, TOD_NORMAL_RATE, TOD_PEAK_RATE,
    MONTHLY_KWH,
)

router = APIRouter()


def get_tariff_rate(hour: int) -> float:
    if hour < 6 or hour >= 22:
        return TOD_OFF_PEAK_RATE
    if hour >= 18:
        return TOD_PEAK_RATE
    return TOD_NORMAL_RATE


@router.get("/kpis")
async def get_kpis(plant_id: int = 1):
    from active_data import active_plant
    return {
        "plant":   PLANT_NAME,
        "period":  REPORT_MONTH,
        "tier":    2,
        "data_source": f"Active: {active_plant.source} ({active_plant.filename})",
        "kpis": {
            "total_kwh":          active_plant.total_kwh,
            "total_kvah":         round(active_plant.total_kwh / max(0.01, active_plant.avg_pf), 1),
            "max_demand_kva":     round(active_plant.peak_kw / max(0.01, active_plant.avg_pf), 1),
            "specific_energy":    active_plant.specific_energy,
            "avg_power_factor":   active_plant.avg_pf,
            "pf_penalty_inr":     SEP_PF_PENALTY_INR if active_plant.avg_pf < 0.90 else 0,
            "md_penalty_inr":     SEP_MD_PENALTY_INR,
            "total_amount_inr":   active_plant.total_bill_inr,
            "production_kg":      SEP_PRODUCTION_KG,
        },
        "baseline_specific_energy":  BASELINE_SEC_ENERGY,
        "current_specific_energy":   active_plant.specific_energy,
        "deviation_pct":             active_plant.deviation_pct,
    }


@router.get("/machine-breakdown")
async def get_machine_breakdown(plant_id: int = 1):
    from active_data import active_plant
    total = active_plant.total_kwh
    machines = []
    status_map = {
        "Air Compressor (75 kW)":           "idle_waste",
        "Hydraulic Press ×3":               "degradation",
        "Lighting & HVAC":                  "pf_issue",
    }
    pf_map = {
        "Induction Furnace (500 kg)": 0.91,
        "Air Compressor (75 kW)":     0.85,
        "Hydraulic Press ×3":         0.88,
        "Fettling Machine ×6":        0.84,
        "Lighting & HVAC":            0.80,
    }
    for m, kwh in active_plant.machines.items():
        machines.append({
            "machine":   m,
            "kwh":       round(kwh, 1),
            "share_pct": round(kwh / max(1.0, total) * 100, 1),
            "avg_pf":    pf_map.get(m, 0.87),
            "status":    status_map.get(m, "normal"),
        })
    return {
        "period":               REPORT_MONTH,
        "total_kwh":            total,
        "machines":             machines,
        "top_waste_machine":    "Air Compressor (75 kW)",
        "potential_saving_inr": TOTAL_ANOMALY_SAVING_INR,
        "note":                 "Machine-level breakdown: active plant state (feeds from uploaded CSV or demo baseline).",
    }


@router.get("/baseline-trend")
async def get_baseline_trend():
    monthly_kg = [9_400, 9_800, 10_600, 11_200, 11_800, SEP_PRODUCTION_KG]
    baseline   = [BASELINE_SEC_ENERGY] * 6
    actual     = [round(kwh / kg, 3) for kwh, kg in zip(MONTHLY_KWH, monthly_kg)]
    return {
        "months":               MONTHS_6,
        "baseline_kwh_per_kg":  baseline,
        "actual_kwh_per_kg":    actual,
        "model":                "LightGBM regression — PLANNED Phase 2 (not yet trained)",
        "features_planned":     ["production_kg", "shift_hours", "max_temp_c"],
        "divergence_start":     "Jun 2026",
        "root_cause":           "Compressor idle waste + Hydraulic Press degradation",
        "note":                 "Baseline is flat reference; actual regression model not yet trained.",
    }


@router.get("/load-profile")
async def get_load_profile(days: int = Query(1, ge=1, le=7)):
    """Synthetic 24-hour load profile — physics simulation."""
    import math, random
    random.seed(42)
    slots = []
    for h in range(24):
        is_working = 6 <= h < 22
        furnace  = 120 + 30 * math.sin(h * 0.4) if is_working else 6
        comp     = 38 + 8 * math.sin(h * 0.3)   if is_working else 4.2
        press    = 55 + 10 * math.sin(h * 0.5)  if 6 <= h < 18 else 0.5
        fettling = 28 + 6 * math.sin(h * 0.6)   if 6 <= h < 18 else 0.3
        hvac     = 10 + 4 * math.sin(h * 0.2)
        total    = furnace + comp + press + fettling + hvac
        slots.append({
            "hour":      f"{h:02d}:00",
            "Furnace":   round(furnace, 1),
            "Compressor":round(comp, 1),
            "Press":     round(press, 1),
            "Fettling":  round(fettling, 1),
            "HVAC":      round(hvac, 1),
            "total_kw":  round(total, 1),
            "tariff":    get_tariff_rate(h),
        })
    return {
        "slots":    slots,
        "note":     "Physics simulation — not from trained NILM model",
        "period":   REPORT_MONTH,
    }


@router.get("/tariff")
async def get_tariff():
    return {
        "state":    "Gujarat",
        "discom":   "PGVCL",
        "currency": "INR",
        "hours": [
            {"hour": h, "rate": get_tariff_rate(h),
             "period": "off_peak" if get_tariff_rate(h) == TOD_OFF_PEAK_RATE
                       else ("peak" if get_tariff_rate(h) == TOD_PEAK_RATE else "normal")}
            for h in range(24)
        ],
    }
