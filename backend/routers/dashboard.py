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
    return {
        "plant":   PLANT_NAME,
        "period":  REPORT_MONTH,
        "tier":    2,
        "data_source": "DISCOM 15-min interval meter CSV",
        "kpis": {
            "total_kwh":          SEP_TOTAL_KWH,
            "total_kvah":         SEP_TOTAL_KVAH,
            "max_demand_kva":     SEP_MAX_DEMAND_KVA,
            "specific_energy":    SEP_SEC_ENERGY,
            "avg_power_factor":   SEP_AVG_PF,
            "pf_penalty_inr":     SEP_PF_PENALTY_INR,
            "md_penalty_inr":     SEP_MD_PENALTY_INR,
            "total_amount_inr":   SEP_TOTAL_AMOUNT_INR,
            "production_kg":      SEP_PRODUCTION_KG,
        },
        "baseline_specific_energy":  BASELINE_SEC_ENERGY,
        "current_specific_energy":   SEP_SEC_ENERGY,
        "deviation_pct":             SEP_DEVIATION_PCT,
    }


@router.get("/machine-breakdown")
async def get_machine_breakdown(plant_id: int = 1):
    total = SEP_TOTAL_KWH
    machines = []
    status_map = {
        "Air Compressor (75 kW)":           "idle_waste",
        "Hydraulic Press ×3":               "degradation",
        "Lighting & HVAC":                  "pf_issue",
    }
    pf_map = {
        "Induction Furnace (500 kg)":  0.91,
        "Air Compressor (75 kW)":      0.85,
        "Hydraulic Press ×3":          0.88,
        "Fettling Machine ×6":         0.84,
        "Lighting & HVAC":             0.80,
    }
    for machine, kwh in MACHINE_KWH.items():
        machines.append({
            "machine":   machine,
            "kwh":       kwh,
            "share_pct": round(kwh / total * 100, 1),
            "avg_pf":    pf_map.get(machine, 0.87),
            "status":    status_map.get(machine, "normal"),
            "method":    "physics-simulation",
        })
    return {
        "period":               REPORT_MONTH,
        "total_kwh":            total,
        "machines":             machines,
        "top_waste_machine":    "Air Compressor (75 kW)",
        "potential_saving_inr": TOTAL_ANOMALY_SAVING_INR,
        "note":                 "Machine-level breakdown: physics simulation (Phase 1). ML disaggregation in Phase 2.",
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
