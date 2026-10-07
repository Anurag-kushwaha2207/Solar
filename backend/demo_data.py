"""
Synthetic demo data generator — Rajkot Foundry Plant
Generates realistic energy time-series, production logs, and machine profiles
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

rng = np.random.default_rng(42)

# ── Machine profiles (kW) ────────────────────────────────────────────────────

MACHINE_PROFILES = {
    "Induction Furnace (500 kg)": {
        "rated_kw": 160,
        "idle_kw": 8,
        "startup_spike": 200,
        "duty_cycle": 0.75,
        "shift_dependent": True,
        "can_shift": True,
    },
    "Air Compressor (75 kW)": {
        "rated_kw": 75,
        "idle_kw": 4.2,     # leaky — idle waste detected here
        "startup_spike": 90,
        "duty_cycle": 0.55,
        "shift_dependent": False,  # runs all the time
        "can_shift": False,
    },
    "Hydraulic Press #1": {
        "rated_kw": 22,
        "idle_kw": 0.5,
        "startup_spike": 28,
        "duty_cycle": 0.60,
        "shift_dependent": True,
        "can_shift": True,
    },
    "Hydraulic Press #2": {
        "rated_kw": 22,
        "idle_kw": 0.5,
        "startup_spike": 28,
        "duty_cycle": 0.60,
        "shift_dependent": True,
        "can_shift": True,
    },
    "Hydraulic Press #3 (degraded)": {
        "rated_kw": 22,
        "idle_kw": 1.8,    # degraded — higher idle
        "startup_spike": 30,
        "duty_cycle": 0.65,
        "shift_dependent": True,
        "can_shift": True,
    },
    "Fettling Machine ×6": {
        "rated_kw": 36,
        "idle_kw": 1.0,
        "startup_spike": 42,
        "duty_cycle": 0.70,
        "shift_dependent": True,
        "can_shift": True,
    },
    "Lighting & HVAC": {
        "rated_kw": 18,
        "idle_kw": 12,
        "startup_spike": 18,
        "duty_cycle": 1.0,
        "shift_dependent": False,
        "can_shift": False,
    },
}

# Gujarat DISCOM ToD tariff (₹/kWh)
TOD_TARIFF = {
    "off_peak": {"hours": list(range(0, 6)) + list(range(22, 24)), "rate": 4.50},
    "normal":   {"hours": list(range(6, 18)),                       "rate": 6.20},
    "peak":     {"hours": list(range(18, 22)),                       "rate": 8.20},
}

def get_tariff_rate(hour: int) -> float:
    if hour in TOD_TARIFF["off_peak"]["hours"]:
        return TOD_TARIFF["off_peak"]["rate"]
    elif hour in TOD_TARIFF["peak"]["hours"]:
        return TOD_TARIFF["peak"]["rate"]
    return TOD_TARIFF["normal"]["rate"]

def simulate_load_profile(n_days: int = 30, interval_min: int = 15) -> pd.DataFrame:
    """Generate synthetic 15-min interval load data for foundry plant."""
    intervals_per_day = 24 * 60 // interval_min
    total_rows = n_days * intervals_per_day

    timestamps = [
        datetime(2026, 9, 1) + timedelta(minutes=i * interval_min)
        for i in range(total_rows)
    ]

    data = []
    for ts in timestamps:
        h = ts.hour
        day = ts.weekday()
        is_working = day < 6  # Mon–Sat
        is_shift_a = 6 <= h < 14
        is_shift_b = 14 <= h < 22
        is_night = h < 6 or h >= 22

        row = {"timestamp": ts}
        total_kw = 0.0

        for machine, prof in MACHINE_PROFILES.items():
            if prof["shift_dependent"]:
                if not is_working or is_night:
                    kw = prof["idle_kw"] * rng.uniform(0.8, 1.1)
                else:
                    kw = prof["rated_kw"] * prof["duty_cycle"] * rng.uniform(0.88, 1.12)
            else:
                if is_night:
                    # Compressor idle at night — the anomaly
                    kw = prof["idle_kw"] * rng.uniform(0.9, 1.1)
                else:
                    kw = prof["rated_kw"] * prof["duty_cycle"] * rng.uniform(0.88, 1.12)

            # Press #3 degradation trend (energy creep over time)
            if "Press #3" in machine:
                day_num = (ts - datetime(2026, 9, 1)).days
                kw *= (1 + 0.003 * day_num)  # 0.3% per day degradation

            row[machine] = round(kw, 2)
            total_kw += kw

        # Power factor varies 0.84–0.92
        pf = 0.88 + 0.04 * np.sin(h * np.pi / 12) + rng.normal(0, 0.01)
        pf = np.clip(pf, 0.82, 0.95)

        row["total_kw"]     = round(total_kw, 2)
        row["power_factor"] = round(pf, 3)
        row["kva"]          = round(total_kw / pf, 2)
        row["tariff_rate"]  = get_tariff_rate(h)
        row["energy_cost"]  = round(total_kw * (interval_min / 60) * get_tariff_rate(h), 2)
        data.append(row)

    return pd.DataFrame(data)


def get_kpi_summary(df: pd.DataFrame) -> Dict:
    """Compute monthly KPIs from load profile DataFrame."""
    interval_h = 0.25  # 15 min
    total_kwh   = df["total_kw"].sum() * interval_h
    peak_kva    = df["kva"].max()
    avg_pf      = df["power_factor"].mean()
    production_kg = 12_580  # from production log

    pf_penalty = max(0, (0.90 - avg_pf) * 100) * 200  # simplified
    md_penalty = max(0, (peak_kva - 200) * 150) if peak_kva > 200 else 0

    return {
        "total_kwh":         round(total_kwh, 0),
        "specific_energy":   round(total_kwh / production_kg, 3),
        "peak_kva":          round(peak_kva, 1),
        "avg_power_factor":  round(avg_pf, 3),
        "pf_penalty_inr":    round(pf_penalty, 0),
        "md_penalty_inr":    round(md_penalty, 0),
        "total_cost_inr":    round(df["energy_cost"].sum(), 0),
        "production_kg":     production_kg,
    }


def get_machine_breakdown(df: pd.DataFrame) -> List[Dict]:
    """Per-machine energy breakdown."""
    interval_h = 0.25
    machines = []
    total = df["total_kw"].sum() * interval_h

    for machine, prof in MACHINE_PROFILES.items():
        kwh = df[machine].sum() * interval_h
        share = round(kwh / total * 100, 1)
        avg_pf = round(df["power_factor"].mean() + rng.uniform(-0.04, 0.03), 3)
        avg_pf = np.clip(avg_pf, 0.78, 0.94)
        status = "normal"
        if "Compressor" in machine:
            status = "idle_waste"
        elif "Press #3" in machine:
            status = "degradation"
        elif "Lighting" in machine and avg_pf < 0.82:
            status = "pf_issue"

        machines.append({
            "machine":   machine,
            "kwh":       round(kwh, 0),
            "share_pct": share,
            "avg_pf":    avg_pf,
            "status":    status,
            "rated_kw":  prof["rated_kw"],
            "can_shift": prof["can_shift"],
        })

    machines.sort(key=lambda x: x["kwh"], reverse=True)
    return machines


def get_anomalies() -> List[Dict]:
    return [
        {
            "id": 1,
            "machine": "Air Compressor (75 kW)",
            "alert_type": "idle_waste",
            "severity": "high",
            "title": "Idle Compressor — Overnight 11 PM to 3 AM",
            "description": "Compressor running during non-production hours. 4.2 kW idle draw detected consistently over 22 nights.",
            "potential_saving_inr": 8400,
            "potential_saving_kwh": 1860,
            "confidence": 0.94,
            "first_detected": "2026-09-03",
            "action": "Install auto-shutoff timer for compressor — estimated ₹2,000 one-time cost.",
        },
        {
            "id": 2,
            "machine": "Induction Furnace (500 kg)",
            "alert_type": "peak_tariff",
            "severity": "medium",
            "title": "Furnace Holding — Peak Tariff Hours 6–10 PM",
            "description": "Induction furnace holds molten metal 6 PM–10 PM when ToD rate is ₹8.20/kWh. Could shift melting to off-peak window.",
            "potential_saving_inr": 10200,
            "potential_saving_kwh": 0,
            "confidence": 0.87,
            "first_detected": "2026-09-01",
            "action": "Reschedule furnace melting to 10 PM–6 AM (off-peak ₹4.50/kWh). See Scheduler tab.",
        },
        {
            "id": 3,
            "machine": "Hydraulic Press #3 (degraded)",
            "alert_type": "degradation",
            "severity": "medium",
            "title": "Motor Degradation — Press #3 Specific Energy Creep",
            "description": "Specific energy of Press #3 increasing: 0.8 kWh/cycle → 1.12 kWh/cycle over 6 weeks (+40%). Bearing wear suspected.",
            "potential_saving_inr": 2800,
            "potential_saving_kwh": 450,
            "confidence": 0.81,
            "first_detected": "2026-08-15",
            "action": "Schedule bearing inspection + greasing. Estimated maintenance cost: ₹3,500, payback: 1.25 months.",
        },
        {
            "id": 4,
            "machine": "All Motors",
            "alert_type": "pf_drop",
            "severity": "low",
            "title": "Power Factor Drop — Capacitor Bank Tuning Required",
            "description": "Average PF dropped from 0.91 to 0.87 over past 4 weeks. DISCOM PF penalty triggered.",
            "potential_saving_inr": 3200,
            "potential_saving_kwh": 0,
            "confidence": 0.98,
            "first_detected": "2026-09-10",
            "action": "Capacitor bank re-tuning by electrician. One-time cost ₹8,000–15,000. Payback: 3–5 months.",
        },
    ]


def get_schedule_jobs() -> List[Dict]:
    return [
        {
            "id": 1, "job_name": "Furnace Melt #1", "machine": "Induction Furnace",
            "duration_h": 3.0, "deadline": "08:00", "constraint": "Deadline: 8AM",
            "current_start": 6/24, "current_end": 9/24,
            "optimal_start": 0/24, "optimal_end": 3/24,
            "saving_inr": 4200, "is_flexible": True, "tariff_shift": "peak→off-peak",
        },
        {
            "id": 2, "job_name": "Furnace Melt #2", "machine": "Induction Furnace",
            "duration_h": 3.0, "deadline": "14:00", "constraint": "Deadline: 2PM",
            "current_start": 15/24, "current_end": 18/24,
            "optimal_start": 10/24, "optimal_end": 13/24,
            "saving_inr": 3800, "is_flexible": True, "tariff_shift": "peak→normal",
        },
        {
            "id": 3, "job_name": "Furnace Safety Hold", "machine": "Induction Furnace",
            "duration_h": 1.0, "deadline": "N/A", "constraint": "Safety-critical",
            "current_start": 9/24, "current_end": 10/24,
            "optimal_start": 9/24, "optimal_end": 10/24,
            "saving_inr": 0, "is_flexible": False, "tariff_shift": "fixed",
        },
        {
            "id": 4, "job_name": "Hydraulic Pressing", "machine": "Hydraulic Press ×3",
            "duration_h": 8.0, "deadline": "17:00", "constraint": "Shift: 8AM–4PM",
            "current_start": 8/24, "current_end": 16/24,
            "optimal_start": 6/24, "optimal_end": 14/24,
            "saving_inr": 1200, "is_flexible": True, "tariff_shift": "normal→normal-early",
        },
        {
            "id": 5, "job_name": "Compressor Auto-Shutoff", "machine": "Air Compressor",
            "duration_h": 14.0, "deadline": "N/A", "constraint": "Auto shutoff 10PM",
            "current_start": 0/24, "current_end": 24/24,
            "optimal_start": 6/24, "optimal_end": 22/24,
            "saving_inr": 8400, "is_flexible": True, "tariff_shift": "always-on→scheduled",
        },
        {
            "id": 6, "job_name": "Fettling Operations", "machine": "Fettling ×6",
            "duration_h": 9.0, "deadline": "17:00", "constraint": "Deadline: 5PM",
            "current_start": 8/24, "current_end": 17/24,
            "optimal_start": 6/24, "optimal_end": 15/24,
            "saving_inr": 2000, "is_flexible": True, "tariff_shift": "normal→normal-early",
        },
    ]


def get_carbon_data() -> Dict:
    """GHG Protocol Scope 1 & 2 carbon data."""
    monthly_kwh = [20800, 21200, 23400, 24000, 25600, 23400]  # Apr–Sep
    CEA_EF = 0.716  # kgCO2/kWh, Western Region 2023

    scope2_monthly = [round(kw * CEA_EF / 1000, 2) for kw in monthly_kwh]  # tCO2e
    scope1_monthly = [2.8, 3.0, 3.2, 3.4, 3.0, 3.2]  # diesel + furnace oil

    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    return {
        "period": "Apr 2026 – Sep 2026",
        "months": months,
        "scope2_monthly": scope2_monthly,
        "scope1_monthly": scope1_monthly,
        "total_scope2":  round(sum(scope2_monthly), 2),
        "total_scope1":  round(sum(scope1_monthly), 2),
        "total_emissions": round(sum(scope2_monthly) + sum(scope1_monthly), 2),
        "emission_intensity": round((sum(scope2_monthly) + sum(scope1_monthly)) / 75480 * 1000, 3),  # kgCO2e/kg
        "cea_emission_factor": CEA_EF,
        "grid_region": "Western Regional Grid",
        "projected_saving_tco2e": 14.2,
        "mv_interventions": [
            {
                "name": "Compressor idle control",
                "baseline_kwh": 2880, "actual_kwh": 1440,
                "saving_kwh": 1440, "co2_avoided_t": 1.03,
                "saving_inr": 8928, "status": "verified",
            },
            {
                "name": "Furnace shift to off-peak ToD",
                "baseline_kwh": 21400, "actual_kwh": 21400,
                "saving_kwh": 0, "co2_avoided_t": 0,
                "saving_inr": 10200, "status": "verified",
                "note": "Tariff saving only, same kWh",
            },
            {
                "name": "Power factor correction (target)",
                "baseline_kwh": None, "actual_kwh": None,
                "saving_kwh": 420, "co2_avoided_t": 0.30,
                "saving_inr": 1400, "status": "projected",
            },
            {
                "name": "Press #3 motor maintenance",
                "baseline_kwh": None, "actual_kwh": None,
                "saving_kwh": 380, "co2_avoided_t": 0.27,
                "saving_inr": 2356, "status": "projected",
            },
        ],
    }


# Pre-generate demo data
_demo_df = simulate_load_profile(30, 15)
_demo_kpis = get_kpi_summary(_demo_df)
_demo_machines = get_machine_breakdown(_demo_df)
_demo_anomalies = get_anomalies()
_demo_schedule = get_schedule_jobs()
_demo_carbon = get_carbon_data()


def get_demo_df() -> pd.DataFrame:
    return _demo_df

def get_demo_kpis() -> Dict:
    return _demo_kpis

def get_demo_machines() -> List[Dict]:
    return _demo_machines

def get_demo_anomalies() -> List[Dict]:
    return _demo_anomalies

def get_demo_schedule() -> List[Dict]:
    return _demo_schedule

def get_demo_carbon() -> Dict:
    return _demo_carbon

def get_tod_tariff() -> Dict:
    return {
        "state": "Gujarat",
        "discom": "UGVCL/PGVCL",
        "currency": "INR",
        "hours": [
            {"hour": h, "rate": get_tariff_rate(h),
             "period": "off_peak" if get_tariff_rate(h) == 4.5 else ("peak" if get_tariff_rate(h) == 8.2 else "normal")}
            for h in range(24)
        ],
    }
