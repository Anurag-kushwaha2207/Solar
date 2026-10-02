"""Scheduler router — wired to real CP-SAT optimiser"""
from fastapi import APIRouter
from pydantic import BaseModel
from cpsat_scheduler import solve_cpsat, DEMO_JOBS, ORTOOLS_AVAILABLE
from constants import SCHEDULER_SAVING_INR_MONTH

router = APIRouter()


class ScheduleRequest(BaseModel):
    plant_id: int = 1
    max_demand_kva: float = 250.0
    optimize_method: str = "cpsat"   # cpsat | greedy
    respect_deadlines: bool = True
    off_peak_priority: bool = True


@router.get("/jobs")
async def get_jobs(plant_id: int = 1):
    """Return current schedule (no optimization) with summary."""
    result = solve_cpsat(DEMO_JOBS, max_demand_kva=250.0, time_limit_s=0.01)
    # For "current" view, use the current_start values
    return {
        "ortools_available": ORTOOLS_AVAILABLE,
        "jobs": result.jobs,
        "current_cost_inr_day":  result.current_cost_inr,
        "optimal_cost_inr_day":  result.optimal_cost_inr,
        "saving_inr_day":        round(result.saving_inr / 25, 1),
        "saving_inr_month":      result.saving_inr,
        "saving_pct":            result.saving_pct,
        "solver_method":         result.method,
        "solver_status":         result.solver_status,
        "solve_time_s":          result.solve_time_s,
    }


@router.post("/optimize")
async def optimize(req: ScheduleRequest):
    """Run real CP-SAT optimisation and return result."""
    result = solve_cpsat(DEMO_JOBS, max_demand_kva=req.max_demand_kva, time_limit_s=5.0)

    return {
        "method":            result.method,
        "ortools_available": ORTOOLS_AVAILABLE,
        "status":            "optimal" if result.feasible else "infeasible",
        "solver_status":     result.solver_status,
        "solve_time_s":      result.solve_time_s,
        "optimized_jobs":    result.jobs,
        "current_cost_inr":  result.current_cost_inr,
        "optimal_cost_inr":  result.optimal_cost_inr,
        "saving_inr_day":    round(result.saving_inr / 25, 1),
        "saving_inr_month":  result.saving_inr,
        "saving_pct":        result.saving_pct,
        "peak_kva":          result.peak_demand_kva,
        "md_respected":      result.md_respected,
        "note":              (
            "REAL CP-SAT result from OR-Tools." if ORTOOLS_AVAILABLE
            else "Greedy fallback (pip install ortools to enable CP-SAT)."
        ),
    }


@router.get("/tariff-heatmap")
async def tariff_heatmap():
    from constants import TOD_OFF_PEAK_RATE, TOD_NORMAL_RATE, TOD_PEAK_RATE
    def rate(h):
        if h < 6 or h >= 22: return TOD_OFF_PEAK_RATE
        if h >= 18: return TOD_PEAK_RATE
        return TOD_NORMAL_RATE
    return {
        "state": "Gujarat", "discom": "PGVCL",
        "hours": [{"hour": h, "rate": rate(h)} for h in range(24)],
    }
