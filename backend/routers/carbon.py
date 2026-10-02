"""
Carbon router — numbers from constants.py (consistent with dashboard & bill)
Emission factor: one place, CEA_EMISSION_FACTOR_KG_PER_KWH = 0.716
"""
from fastapi import APIRouter
from constants import (
    PLANT_NAME, REPORT_PERIOD, MONTHS_6,
    CEA_EMISSION_FACTOR_KG_PER_KWH, EF_SOURCE, GRID_REGION,
    DIESEL_EF_KG_PER_LITRE,
    SEP_TOTAL_KWH, SEP_SCOPE2_TCO2E, SEP_SCOPE1_TCO2E, SEP_TOTAL_TCO2E,
    SEP_EMISSION_INTENSITY, SEP_PRODUCTION_KG,
    MONTHLY_SCOPE1, MONTHLY_SCOPE2, MONTHLY_KWH,
    COMPRESSOR_SAVING_KWH, COMPRESSOR_CO2_T, COMPRESSOR_SAVING_INR,
    PF_SAVING_KWH, PF_CO2_T, PF_SAVING_INR,
    ANOMALY_SAVING_FURNACE_INR, PROJECTED_SAVING_TCO2E_YEAR,
)

router = APIRouter()


@router.get("/report")
async def get_report(plant_id: int = 1):
    total_scope1 = round(sum(MONTHLY_SCOPE1), 2)
    total_scope2 = round(sum(MONTHLY_SCOPE2), 2)

    return {
        "plant":    PLANT_NAME,
        "standard": "GHG Protocol Corporate Standard",
        "boundary": "Operational Control — Single Plant",
        "period":   REPORT_PERIOD,
        "scope2": {
            "monthly_tco2e":    MONTHLY_SCOPE2,
            "sep_tco2e":        SEP_SCOPE2_TCO2E,
            "total_tco2e":      total_scope2,
            "method":           "Location-based",
            "emission_factor":  CEA_EMISSION_FACTOR_KG_PER_KWH,
            "ef_source":        EF_SOURCE,
            "calc_sep":         f"{SEP_TOTAL_KWH:,} kWh × {CEA_EMISSION_FACTOR_KG_PER_KWH} kg/kWh ÷ 1000 = {SEP_SCOPE2_TCO2E} tCO₂e",
        },
        "scope1": {
            "monthly_tco2e":    MONTHLY_SCOPE1,
            "sep_tco2e":        SEP_SCOPE1_TCO2E,
            "total_tco2e":      total_scope1,
            "sources":          ["Diesel generator", "Furnace oil"],
            "ipcc_factor_diesel": DIESEL_EF_KG_PER_LITRE,
        },
        "combined": {
            "months":                   MONTHS_6,
            "scope1":                   MONTHLY_SCOPE1,
            "scope2":                   MONTHLY_SCOPE2,
            "total_tco2e":              round(total_scope1 + total_scope2, 2),
            "sep_total":                SEP_TOTAL_TCO2E,
            "intensity_kg_per_kg":      SEP_EMISSION_INTENSITY,
            "projected_saving_tco2e":   PROJECTED_SAVING_TCO2E_YEAR,
        },
        "mv_table": [
            {
                "name":           "Compressor idle-elimination (verified simulation)",
                "baseline_kwh":   COMPRESSOR_SAVING_KWH * 2,   # 740 kWh was wasted
                "actual_kwh":     COMPRESSOR_SAVING_KWH,        # 370 remaining
                "saving_kwh":     COMPRESSOR_SAVING_KWH,
                "co2_avoided_t":  COMPRESSOR_CO2_T,
                "saving_inr":     int(COMPRESSOR_SAVING_INR),
                "status":         "simulated",
                "note":           "Based on measured 4.2 kW idle draw × 4h × 22 nights",
            },
            {
                "name":           "Furnace ToD shift (tariff saving only)",
                "baseline_kwh":   None,
                "actual_kwh":     None,
                "saving_kwh":     0,
                "co2_avoided_t":  0.0,
                "saving_inr":     ANOMALY_SAVING_FURNACE_INR,
                "status":         "simulated",
                "note":           "Same kWh, cheaper tariff window — no CO₂ reduction",
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
        ],
        "audit_trail": [
            {"action": "DISCOM interval data ingested",   "detail": f"{SEP_TOTAL_KWH:,} kWh · 15-min · {MONTHS_6[-1]} 2026"},
            {"action": "Scope 2 calculated",              "detail": f"{SEP_TOTAL_KWH:,} × {CEA_EMISSION_FACTOR_KG_PER_KWH} ÷ 1000 = {SEP_SCOPE2_TCO2E} tCO₂e"},
            {"action": "Scope 1 — diesel log entered",    "detail": f"Sep: {SEP_SCOPE1_TCO2E} tCO₂e"},
            {"action": "Emission factor source",          "detail": EF_SOURCE},
            {"action": "Verification status",             "detail": "Phase 1 simulation — third-party verification not yet done"},
        ],
        "buyer_readiness": {
            "scope2_location_based":    True,
            "scope1_direct":            True,
            "ghg_protocol_aligned":     True,
            "emission_intensity_metric":True,
            "machine_readable_api":     True,
            "third_party_verified":     False,
            "note":                     "Phase 1 prototype — engage certified verifier before regulatory disclosure",
        },
    }


@router.get("/intensity-trend")
async def intensity_trend():
    monthly_kg = [9_400, 9_800, 10_600, 11_200, 11_800, SEP_PRODUCTION_KG]
    intensities = [
        round((s1 + s2) * 1000 / kg, 3)
        for s1, s2, kg in zip(MONTHLY_SCOPE1, MONTHLY_SCOPE2, monthly_kg)
    ]
    return {
        "months":    MONTHS_6,
        "intensity": intensities,
        "target_intensity": 2.45,
        "unit": "kgCO2e per kg casting",
    }
