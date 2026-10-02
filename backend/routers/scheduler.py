"""
Scheduler router — wired to real CP-SAT + Greedy.
PPO/RL is NOT implemented and is NOT exposed in this API.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from cpsat_scheduler import solve_cpsat, solve_both, _greedy, DEMO_JOBS, ORTOOLS_AVAILABLE
from constants import (
    TOD_OFF_PEAK_RATE, TOD_NORMAL_RATE, TOD_PEAK_RATE,
    SCHEDULER_SAVING_INR_MONTH, SCHEDULER_SAVING_PCT,
)

router = APIRouter()


class ScheduleRequest(BaseModel):
    plant_id: int = 1
    max_demand_kva: float = 250.0
    time_limit_s: float = 8.0


@router.get("/jobs")
async def get_jobs(plant_id: int = 1):
    """Current (unoptimized) schedule + summary."""
    cpsat = solve_cpsat(DEMO_JOBS, time_limit_s=0.05)  # fast feasibility check
    return {
        "ortools_available": ORTOOLS_AVAILABLE,
        "jobs": cpsat.jobs,
        "current_cost_inr_day": cpsat.current_cost_inr,
        "energy_kwh_day":       cpsat.energy_kwh_day,
        "energy_kwh_month_est": round(cpsat.energy_kwh_day * 26, 0),
        "note": (
            f"Daily scheduled energy {cpsat.energy_kwh_day} kWh x 26 working days "
            f"= ~{cpsat.energy_kwh_day * 26:.0f} kWh (excl. HVAC base load ~6,940 kWh/month)"
        ),
    }


@router.post("/optimize")
async def optimize(req: ScheduleRequest):
    """Run real CP-SAT optimisation. Returns optimal start slots + savings."""
    result = solve_cpsat(DEMO_JOBS, max_demand_kva=req.max_demand_kva, time_limit_s=req.time_limit_s)
    return {
        "method":             result.method,
        "ortools_available":  ORTOOLS_AVAILABLE,
        "solver_status":      result.solver_status,
        "solve_time_s":       result.solve_time_s,
        "optimized_jobs":     result.jobs,
        "current_cost_inr":   result.current_cost_inr,
        "optimal_cost_inr":   result.optimal_cost_inr,
        "saving_inr_day":     result.saving_inr_day,
        "saving_inr_month":   result.saving_inr_month,
        "saving_pct":         result.saving_pct,
        "energy_kwh_day":     result.energy_kwh_day,
        "peak_kva":           result.peak_demand_kva,
        "md_respected":       result.md_respected,
        "note": (
            "REAL CP-SAT result (OR-Tools 9.x). "
            "Saving is from furnace ToD shift: normal/peak -> off-peak. "
            "Compressor saving (idle elimination) shown in Anomaly tab separately."
        ),
    }


@router.get("/compare")
async def compare_methods(plant_id: int = 1):
    """
    Run CP-SAT and Greedy, return side-by-side comparison.
    PPO/RL is planned but NOT implemented — it is NOT included in this response.
    """
    both = solve_both(DEMO_JOBS)
    return {
        "comparison":    both["comparison"],
        "cpsat_jobs":    both["cpsat"].jobs,
        "greedy_jobs":   both["greedy"].jobs,
        "note": (
            "Only CP-SAT and Greedy are implemented. "
            "PPO/RL scheduling is listed as a Phase 2 feature — not yet trained or deployed."
        ),
    }


@router.get("/tariff-heatmap")
async def tariff_heatmap():
    def rate(h):
        if h < 6 or h >= 22: return TOD_OFF_PEAK_RATE
        if h >= 18:           return TOD_PEAK_RATE
        return TOD_NORMAL_RATE
    return {
        "state": "Gujarat",
        "discom": "PGVCL",
        "source": "PGVCL Tariff Order 2024-25",
        "hours": [{"hour": h, "rate": rate(h), "label": (
            "off-peak" if (h < 6 or h >= 22) else
            "peak" if h >= 18 else "normal"
        )} for h in range(24)],
    }
