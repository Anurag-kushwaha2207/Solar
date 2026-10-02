"""
NILM Disaggregation router — HONEST version
Clearly labels results as physics-based simulation (Phase 1).
Real ML training (IMDELD/HIPE) planned for Phase 2.
"""
from fastapi import APIRouter
from constants import (
    MACHINE_KWH, SEP_TOTAL_KWH,
    NILM_STATUS, NILM_MODEL_DESC,
)

router = APIRouter()


@router.get("/disaggregate")
async def disaggregate(plant_id: int = 1):
    """
    NILM disaggregation result.

    Phase 1 Prototype: Results are physics-based simulation using
    equipment register + duty-cycle estimates, NOT from a trained ML model.
    A Seq2Point model on IMDELD dataset is planned for Phase 2.
    """
    total = SEP_TOTAL_KWH
    machine_results = []
    for machine, kwh in MACHINE_KWH.items():
        machine_results.append({
            "machine":    machine,
            "kwh":        kwh,
            "share_pct":  round(kwh / total * 100, 1),
            "method":     "physics-simulation",
            "confidence": None,   # No confidence score — simulation, not ML
        })

    return {
        "status":      NILM_STATUS,      # "SIMULATED"
        "model":       NILM_MODEL_DESC,
        "phase":       "Phase 1 Prototype",
        "data_tier":   2,
        "resolution":  "15-min",
        "total_kwh":   total,
        "machines":    machine_results,
        "honest_note": (
            "Numbers are from physics-based simulation (equipment register + duty cycles). "
            "NOT from a trained NILM model. "
            "Phase 2 target: train Seq2Point on IMDELD (pelletizer/contactor/fan dataset). "
            "No external paper results are attributed here."
        ),
        # Planned Phase 2 experiments — clearly NOT our results
        "phase2_plan": {
            "status":   "NOT YET EXECUTED",
            "datasets": [
                "IMDELD — industrial motors, fans, contactors (15-min, 3-phase)",
                "HIPE — HochEnergiePhysik Electronics (5-sec, single-phase)",
            ],
            "models_to_try": [
                "Seq2Point (baseline NILM)",
                "Transformer-based NILM (if compute available)",
            ],
            "resolutions": ["1-sec", "15-min", "30-min"],
            "hypothesis": (
                "Physical constraints + equipment-register pretraining "
                "should improve accuracy at 15-min vs naive disaggregation."
            ),
            "warning": (
                "No published paper results are claimed for this prototype. "
                "Literature benchmarks will be cited only after our own experiments confirm them."
            ),
        },
    }


@router.get("/status")
async def nilm_status():
    return {
        "phase":   1,
        "status":  NILM_STATUS,
        "model":   "Physics simulation",
        "next":    "Phase 2: Seq2Point on IMDELD",
        "metrics": {
            "our_result": None,
            "note": "No metrics to report — model not yet trained.",
        },
    }
