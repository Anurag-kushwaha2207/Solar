"""Dashboard router — KPIs, load profile, machine breakdown"""
from fastapi import APIRouter, Query
from demo_data import get_demo_kpis, get_demo_machines, get_demo_df, get_tod_tariff
import numpy as np

router = APIRouter()


@router.get("/kpis")
async def get_kpis(plant_id: int = 1):
    """Monthly KPI summary for the plant."""
    kpis = get_demo_kpis()
    return {
        "plant": "Rajkot Precision Foundry",
        "period": "Sep 2026",
        "tier": 2,
        "confidence": 0.78,
        "kpis": kpis,
        "baseline_specific_energy": 3.42,
        "current_specific_energy": kpis["specific_energy"],
        "deviation_pct": round((kpis["specific_energy"] - 3.42) / 3.42 * 100, 1),
    }


@router.get("/load-profile")
async def get_load_profile(
    days: int = Query(1, ge=1, le=30),
    resolution: str = Query("15min", regex="^(15min|30min|1h)$"),
):
    """24-hour load profile with machine disaggregation."""
    df = get_demo_df()
    # Return last `days` days, resampled to resolution
    resample_map = {"15min": "15T", "30min": "30T", "1h": "1h"}
    subset = df.tail(24 * 4 * days)  # 15-min slots

    machines = list(subset.columns[1:-4])  # exclude timestamp + totals
    hours = [r["timestamp"].strftime("%H:%M") for _, r in subset.iterrows()]

    return {
        "timestamps": hours[::1],
        "machines": machines,
        "data": {m: [round(v, 2) for v in subset[m].tolist()] for m in machines},
        "total_kw": [round(v, 2) for v in subset["total_kw"].tolist()],
        "power_factor": [round(v, 3) for v in subset["power_factor"].tolist()],
        "tariff_rate": [round(v, 2) for v in subset["tariff_rate"].tolist()],
    }


@router.get("/machine-breakdown")
async def get_machine_breakdown(plant_id: int = 1):
    """Per-machine energy consumption breakdown."""
    machines = get_demo_machines()
    total = sum(m["kwh"] for m in machines)
    return {
        "period": "Sep 2026",
        "total_kwh": total,
        "machines": machines,
        "top_waste_machine": "Air Compressor (75 kW)",
        "potential_saving_inr": 22800,
    }


@router.get("/baseline-trend")
async def get_baseline_trend():
    """6-month baseline vs actual specific energy trend."""
    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    baseline = [3.42, 3.45, 3.40, 3.48, 3.44, 3.42]
    actual   = [3.45, 3.50, 3.62, 3.75, 3.80, 3.84]
    return {
        "months": months,
        "baseline_kwh_per_kg": baseline,
        "actual_kwh_per_kg": actual,
        "model": "LightGBM regression · R²=0.91",
        "features": ["production_kg", "shift_hours", "max_temp_c"],
        "divergence_start": "Jun 2026",
        "root_cause": "Compressor idle waste + Press #3 degradation",
    }


@router.get("/tariff")
async def get_tariff():
    """ToD tariff schedule."""
    return get_tod_tariff()
