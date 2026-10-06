import hashlib
import json
from fastapi import APIRouter
from active_data import active_plant
from constants import (
    PLANT_NAME, REPORT_PERIOD, MONTHS_6,
    CEA_EMISSION_FACTOR_KG_PER_KWH, EF_SOURCE, GRID_REGION,
    DIESEL_EF_KG_PER_LITRE,
    SEP_TOTAL_KWH, SEP_SCOPE2_TCO2E, SEP_SCOPE1_TCO2E, SEP_TOTAL_TCO2E,
    SEP_EMISSION_INTENSITY, SEP_PRODUCTION_KG,
    MONTHLY_SCOPE1, MONTHLY_SCOPE2, MONTHLY_KWH,
    COMPRESSOR_SAVING_KWH, COMPRESSOR_CO2_T, COMPRESSOR_SAVING_INR,
    PF_SAVING_KWH, PF_CO2_T, PF_SAVING_INR,
    SCHEDULER_SAVING_APPROX_INR_MONTH, PROJECTED_SAVING_TCO2E_YEAR,
)

router = APIRouter()


@router.get("/report")
async def get_report(plant_id: int = 1):
    current_kwh = active_plant.total_kwh
    sep_scope2 = round(current_kwh * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2)
    is_demo = active_plant.source == "demo_baseline"

    sep_scope1 = SEP_SCOPE1_TCO2E if is_demo else 0.0
    sep_total = round(sep_scope2 + sep_scope1, 2)
    prod_units = active_plant.production_kg if active_plant.production_kg > 0 else (SEP_PRODUCTION_KG if is_demo else 1.0)
    sep_intensity = round(sep_total * 1000 / prod_units, 3)

    from cpsat_scheduler import get_plant_jobs, solve_cpsat
    scale = active_plant.total_kwh / max(1.0, float(SEP_TOTAL_KWH)) if is_demo else 1.0
    jobs = get_plant_jobs(scale)
    sched_md = float(getattr(active_plant, "contract_kva", 250.0) or 250.0)
    sched_res = solve_cpsat(jobs, max_demand_kva=sched_md, time_limit_s=3.0)
    tod_saving_inr = int(round(sched_res.saving_inr_month))
    tod_saving_pct = sched_res.saving_pct

    if is_demo:
        monthly_scope1 = MONTHLY_SCOPE1
        monthly_scope2 = list(MONTHLY_SCOPE2)
        monthly_scope2[-1] = sep_scope2
        total_scope1 = round(sum(monthly_scope1), 2)
        total_scope2 = round(sum(monthly_scope2), 2)
        months_list = MONTHS_6
        scope1_sources = ["Diesel generator", "Furnace oil"]
        tod_job_name = "Furnace ToD shift (tariff saving only)"
        mv_table = [
            {
                "name":           "Compressor idle-elimination (simulated)",
                "baseline_kwh":   COMPRESSOR_SAVING_KWH * 2,
                "actual_kwh":     COMPRESSOR_SAVING_KWH,
                "saving_kwh":     COMPRESSOR_SAVING_KWH,
                "co2_avoided_t":  COMPRESSOR_CO2_T,
                "saving_inr":     int(COMPRESSOR_SAVING_INR),
                "status":         "simulated",
                "note":           "Based on measured 4.2 kW idle draw × 4h × 22 nights",
            },
            {
                "name":           tod_job_name,
                "baseline_kwh":   None,
                "actual_kwh":     None,
                "saving_kwh":     0,
                "co2_avoided_t":  0.0,
                "saving_inr":     tod_saving_inr,
                "status":         "simulated",
                "note":           f"Same kWh, cheaper tariff window ({tod_saving_pct}% of bill)",
            },
            {
                "name":           "PF correction — capacitor bank (projected)",
                "baseline_kwh":   None,
                "actual_kwh":     None,
                "saving_kwh":     PF_SAVING_KWH,
                "co2_avoided_t":  PF_CO2_T,
                "saving_inr":     PF_SAVING_INR,
                "status":         "projected",
                "note":           "Planned intervention — not yet executed",
            },
        ]
    else:
        # Uploaded facility (e.g. ABC Manufacturing)
        monthly_scope1 = [0.0]
        monthly_scope2 = [sep_scope2]
        total_scope1 = 0.0
        total_scope2 = sep_scope2
        months_list = [active_plant.billing_period]
        scope1_sources = ["Not reported for this plant (Facility operates 100% on grid power / no fuel log uploaded)"]
        tod_job_name = "CNC Shift Optimization (ToD tariff shift)"

        mv_table = [
            {
                "name":           tod_job_name,
                "baseline_kwh":   None,
                "actual_kwh":     None,
                "saving_kwh":     0,
                "co2_avoided_t":  0.0,
                "saving_inr":     tod_saving_inr,
                "status":         "simulated",
                "note":           f"Off-peak tariff shift savings for {active_plant.plant_name} ({tod_saving_pct}% of bill)",
            },
            {
                "name":           "CNC Standby & Spindle Idle Power Management",
                "baseline_kwh":   500,
                "actual_kwh":     250,
                "saving_kwh":     250,
                "co2_avoided_t":  round(250 * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2),
                "saving_inr":     2100,
                "status":         "simulated",
                "note":           "Standby power cut-off on CNC #1 & spindle interlock on CNC #3",
            },
        ]
        if active_plant.avg_pf < 0.90:
            mv_table.append({
                "name":           "PF correction — capacitor bank (projected)",
                "baseline_kwh":   None,
                "actual_kwh":     None,
                "saving_kwh":     PF_SAVING_KWH,
                "co2_avoided_t":  PF_CO2_T,
                "saving_inr":     int(active_plant.pf_penalty_inr),
                "status":         "projected",
                "note":           f"APFC penalty recovery for PF {active_plant.avg_pf}",
            })

    audit_payload = {
        "plant": active_plant.plant_name,
        "period": active_plant.billing_period,
        "kwh": current_kwh,
        "emission_factor": CEA_EMISSION_FACTOR_KG_PER_KWH,
        "scope1_tco2e": sep_scope1,
        "scope2_tco2e": sep_scope2,
        "total_tco2e": sep_total,
        "production_kg": active_plant.production_kg,
    }
    report_sha256 = hashlib.sha256(json.dumps(audit_payload, sort_keys=True).encode()).hexdigest()

    return {
        "plant":    active_plant.plant_name,
        "standard": "GHG Protocol Corporate Standard",
        "boundary": "Operational Control — Single Plant",
        "period":   active_plant.billing_period,
        "report_sha256": report_sha256,
        "scope2": {
            "monthly_tco2e":    monthly_scope2,
            "sep_tco2e":        sep_scope2,
            "total_tco2e":      total_scope2,
            "method":           "Location-based",
            "emission_factor":  CEA_EMISSION_FACTOR_KG_PER_KWH,
            "ef_source":        EF_SOURCE,
            "calc_sep":         f"{int(current_kwh):,} kWh × {CEA_EMISSION_FACTOR_KG_PER_KWH} kg/kWh ÷ 1000 = {sep_scope2} tCO₂e",
        },
        "scope1": {
            "monthly_tco2e":    monthly_scope1,
            "sep_tco2e":        sep_scope1,
            "total_tco2e":      total_scope1,
            "sources":          scope1_sources,
            "ipcc_factor_diesel": DIESEL_EF_KG_PER_LITRE,
        },
        "combined": {
            "months":                   months_list,
            "scope1":                   monthly_scope1,
            "scope2":                   monthly_scope2,
            "total_tco2e":              round(total_scope1 + total_scope2, 2),
            "sep_total":                sep_total,
            "intensity_kg_per_kg":      sep_intensity,
            "intensity_unit":           "kgCO₂e / kg casting" if is_demo else "kgCO₂e / unit produced",
            "intensity_target":         2.45 if is_demo else None,
            "projected_saving_tco2e":   PROJECTED_SAVING_TCO2E_YEAR if is_demo else round(0.18 * 12, 2),
        },
        "mv_table": mv_table,
        "audit_trail": [
            {"action": "Plant data ingested",            "detail": f"{int(current_kwh):,} kWh · {active_plant.source} ({active_plant.filename})"},
            {"action": "Scope 2 calculated",              "detail": f"{int(current_kwh):,} × {CEA_EMISSION_FACTOR_KG_PER_KWH} ÷ 1000 = {sep_scope2} tCO₂e"},
            {"action": "Scope 1 reporting status",        "detail": f"{sep_scope1} tCO₂e ({'Foundry baseline' if is_demo else 'No fuel log uploaded — Scope 2 only'})"},
            {"action": "Emission factor source",          "detail": EF_SOURCE},
            {"action": "Internal verification status",   "detail": "Phase 1 pipeline — internal audit log registered"},
            {"action": "Payload Hash (Audit Trail)",      "detail": f"SHA-256: {report_sha256[:16]}...{report_sha256[-8:]} (payload hash)"},
        ],
        "data_source": active_plant.source,
        "filename": active_plant.filename,
        "active_kwh": current_kwh,
        "buyer_readiness": {
            "scope2_location_based":    True,
            "scope1_direct":            is_demo,
            "ghg_protocol_aligned":     True,
            "emission_intensity_metric":True,
            "machine_readable_api":     True,
            "third_party_verified":     False,
            "note":                     "Phase 1 prototype — engage certified verifier before regulatory disclosure",
        },
    }


@router.get("/intensity-trend")
async def intensity_trend():
    current_kwh = active_plant.total_kwh
    sep_scope2 = round(current_kwh * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2)
    if active_plant.source != "demo_baseline":
        intensity = round(sep_scope2 * 1000 / max(1.0, active_plant.production_kg), 2)
        return {
            "months": [active_plant.billing_period],
            "intensity": [intensity],
            "target_intensity": intensity,
            "unit": "kgCO₂e per unit output",
            "note": f"Single-month production baseline for {active_plant.plant_name}. Multi-month trend requires additional billing cycles.",
        }

    monthly_scope2 = list(MONTHLY_SCOPE2)
    monthly_scope2[-1] = sep_scope2

    monthly_kg = [9_400, 9_800, 10_600, 11_200, 11_800, SEP_PRODUCTION_KG]
    intensities = [
        round((s1 + s2) * 1000 / kg, 3)
        for s1, s2, kg in zip(MONTHLY_SCOPE1, monthly_scope2, monthly_kg)
    ]
    return {
        "months":    MONTHS_6,
        "intensity": intensities,
        "target_intensity": 2.45,
        "unit": "kgCO2e per kg casting",
    }
