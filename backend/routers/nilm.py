"""
NILM Disaggregation router — HONEST version
Clearly labels results as physics-based simulation (Phase 1).
Real ML training (IMDELD/HIPE) planned for Phase 2.
"""
from fastapi import APIRouter
from constants import (
    MACHINE_KWH, SEP_TOTAL_KWH,
    NILM_STATUS, NILM_MODEL_DESC,
    NILM_TARGET_R2_1SEC, NILM_TARGET_R2_15MIN, NILM_TARGET_R2_30MIN,
)

router = APIRouter()


@router.get("/disaggregate")
async def disaggregate(plant_id: int = 1):
    """
    NILM disaggregation result.

    ⚠ PHASE 1 PROTOTYPE: Results are physics-based simulation,
      NOT from a trained ML model. A Transformer/Seq2Point model
      trained on IMDELD dataset is planned for Phase 2.
    """
    total = SEP_TOTAL_KWH
    machine_results = []
    for machine, kwh in MACHINE_KWH.items():
        machine_results.append({
            "machine":   machine,
            "kwh":       kwh,
            "share_pct": round(kwh / total * 100, 1),
            "method":    "physics-simulation",
            "confidence": None,   # No confidence score for simulated data
        })

    return {
        "status":        NILM_STATUS,          # "SIMULATED"
        "model":         NILM_MODEL_DESC,
        "phase":         "Phase 1 Prototype",
        "data_tier":     2,
        "resolution":    "15-min",
        "total_kwh":     total,
        "machines":      machine_results,
        "honest_note":   (
            "These numbers come from a physics-based simulation "
            "using equipment register duty cycles, NOT a trained NILM model. "
            "ML training on IMDELD/HIPE is Phase 2 work."
        ),
        # Target metrics from literature (NOT our experiment results)
        "literature_targets": {
            "note": "From published papers — NOT our own experiment results",
            "transformer_nilm_industrial_r2": "~0.89–0.94 (1-sec data, Bouzbita et al. 2024)",
            "seq2point_15min_r2": "~0.71–0.87 (estimated with physical constraints)",
        },
        "ablation_plan": {
            "description": "Planned Phase 2 ML training and benchmark on IEEE DataPort IMDELD / HIPE",
            "datasets": ["HIPE (5-sec high-res electronics manufacturing)", "IMDELD (industrial pelletizers, contactors, fans)"],
            "resolutions_to_test": ["1-sec", "1-min", "15-min", "30-min"],
            "status": "PHASE_2_PLANNED (Oct 11 - Nov 22)",
        },
        "physical_constraints": "sum_to_total=True, non_negative=True",
    }


try:
    from imdeld_baseline import run_resolution_ablation_experiment
    _ABLATION_CACHE = run_resolution_ablation_experiment()
except Exception as _e:
    _ABLATION_CACHE = {
        "status": "UNAVAILABLE",
        "error": str(_e),
        "note": "Scikit-learn and pandas required to run resolution ablation experiment.",
        "phase": "Phase 1 Prototype",
    }


@router.get("/resolution-ablation")
async def resolution_ablation():
    """
    Resolution vs Accuracy Ablation on Synthetic Industrial Duty-Cycle Simulation.
    Evaluates 1-minute vs 15-minute (DISCOM standard) vs 30-minute interval data.
    Clearly discloses this as a prototype synthetic benchmark; real IMDELD training is Phase 2.
    """
    return _ABLATION_CACHE

