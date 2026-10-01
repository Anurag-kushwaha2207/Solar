"""Carbon Report router — GHG Protocol Scope 1 & 2"""
from fastapi import APIRouter
from demo_data import get_demo_carbon

router = APIRouter()

@router.get("/report")
async def get_report(plant_id: int = 1):
    data = get_demo_carbon()
    return {
        "plant": "Rajkot Precision Foundry Pvt. Ltd.",
        "standard": "GHG Protocol Corporate Standard",
        "boundary": "Operational Control — Single Plant",
        "period": data["period"],
        "scope2": {
            "monthly_tco2e": data["scope2_monthly"],
            "total_tco2e": data["total_scope2"],
            "method": "Location-based",
            "emission_factor": data["cea_emission_factor"],
            "ef_source": "CEA India 2023 — Western Regional Grid",
        },
        "scope1": {
            "monthly_tco2e": data["scope1_monthly"],
            "total_tco2e": data["total_scope1"],
            "sources": ["Diesel generator", "Furnace oil"],
            "ipcc_factor_diesel": 2.68,
        },
        "combined": {
            "months": data["months"],
            "scope1": data["scope1_monthly"],
            "scope2": data["scope2_monthly"],
            "total": data["total_emissions"],
            "intensity_kg_per_kg": data["emission_intensity"],
            "projected_saving_tco2e": data["projected_saving_tco2e"],
        },
        "mv_table": data["mv_interventions"],
        "buyer_readiness": {
            "scope2_location_based": True,
            "scope1_direct": True,
            "ghg_protocol_aligned": True,
            "emission_intensity_metric": True,
            "machine_readable_api": True,
            "third_party_verified": False,
        },
        "audit_trail": [
            {"action": "DISCOM meter data ingested", "detail": "48,240 kWh · 30-min · Sep 2026"},
            {"action": "Scope 2 calculated", "detail": "48,240 × 0.716 = 34.54 tCO₂e (Sep 2026)"},
            {"action": "Scope 1 — Diesel log", "detail": "320L × 2.68 = 0.86 tCO₂e (Sep 2026)"},
            {"action": "M&V baseline trained", "detail": "LightGBM R²=0.91 · Apr–Aug data"},
            {"action": "Report signed", "detail": "SHA-256 hash: a4f2e8c3... · v1.0"},
        ],
    }

@router.get("/intensity-trend")
async def intensity_trend():
    return {
        "months": ["Apr","May","Jun","Jul","Aug","Sep"],
        "intensity": [2.48, 2.52, 2.61, 2.68, 2.71, 2.74],
        "target_intensity": 2.45,
        "unit": "kgCO2e per kg casting",
    }

@router.get("/buyer-disclosure/{format}")
async def buyer_disclosure(format: str = "json"):
    data = get_demo_carbon()
    if format == "cbam":
        return {
            "format": "CBAM-style",
            "embedded_carbon_per_tonne": round(data["emission_intensity"], 3),
            "scope": "1+2",
            "period": data["period"],
            "verified": False,
            "note": "Engage certified verifier for regulatory compliance",
        }
    return {"format": "json", "data": get_demo_carbon()}
