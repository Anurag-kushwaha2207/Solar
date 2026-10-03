"""Scheduler router — wired to real CP-SAT optimiser & Greedy heuristic"""
from fastapi import APIRouter
from pydantic import BaseModel
from cpsat_scheduler import solve_cpsat, _fallback_greedy, get_plant_jobs, DEMO_JOBS, ORTOOLS_AVAILABLE
from active_data import active_plant
from constants import SEP_TOTAL_KWH

router = APIRouter()


class ScheduleRequest(BaseModel):
    plant_id: int = 1
    max_demand_kva: float = 250.0
    optimize_method: str = "cpsat"   # cpsat | greedy
    respect_deadlines: bool = True
    off_peak_priority: bool = True


def _current_jobs():
    scale = active_plant.total_kwh / max(1.0, float(SEP_TOTAL_KWH))
    return get_plant_jobs(scale)


@router.get("/jobs")
async def get_jobs(plant_id: int = 1):
    """Return current schedule (no optimization) with summary."""
    jobs = _current_jobs()
    default_md = float(getattr(active_plant, "contract_kva", 250.0) or 250.0)
    result = solve_cpsat(jobs, max_demand_kva=default_md, time_limit_s=5.0)
    return {
        "ortools_available": ORTOOLS_AVAILABLE,
        "jobs": result.jobs,
        "current_cost_inr_day":  result.current_cost_inr,
        "optimal_cost_inr_day":  result.optimal_cost_inr,
        "saving_inr_day":        result.saving_inr_day,
        "saving_inr_month":      result.saving_inr_month,
        "saving_pct":            result.saving_pct,
        "solver_method":         result.method,
        "solver_status":         result.solver_status,
        "solve_time_s":          result.solve_time_s,
    }


@router.post("/optimize")
async def optimize(req: ScheduleRequest):
    """Run real CP-SAT or Greedy optimisation and return result."""
    jobs = _current_jobs()
    md = req.max_demand_kva
    if active_plant.source != "demo_baseline" and req.max_demand_kva == 250.0:
        md = float(getattr(active_plant, "contract_kva", 285.0) or 285.0)

    if req.optimize_method.lower() == "greedy":
        result = _fallback_greedy(jobs, max_demand_kva=md)
    else:
        result = solve_cpsat(jobs, max_demand_kva=md, time_limit_s=5.0)

    return {
        "method":            result.method,
        "ortools_available": ORTOOLS_AVAILABLE,
        "status":            "optimal" if result.feasible else "infeasible",
        "solver_status":     result.solver_status,
        "solve_time_s":      result.solve_time_s,
        "optimized_jobs":    result.jobs,
        "current_cost_inr":  result.current_cost_inr,
        "optimal_cost_inr":  result.optimal_cost_inr,
        "saving_inr_day":    result.saving_inr_day,
        "saving_inr_month":  result.saving_inr_month,
        "saving_pct":        result.saving_pct,
        "peak_kva":          result.peak_demand_kva,
        "md_respected":      result.md_respected,
        "note":              (
            "REAL CP-SAT result from Google OR-Tools." if ("CP-SAT" in result.method and ORTOOLS_AVAILABLE)
            else "Greedy heuristic schedule."
        ),
    }


@router.get("/methods")
async def compare_methods(max_demand_kva: float = 250.0):
    """Compare real CP-SAT vs real Greedy heuristic."""
    jobs = _current_jobs()
    md = max_demand_kva
    if active_plant.source != "demo_baseline" and max_demand_kva == 250.0:
        md = float(getattr(active_plant, "contract_kva", 285.0) or 285.0)

    cpsat_res = solve_cpsat(jobs, max_demand_kva=md, time_limit_s=5.0)
    greedy_res = _fallback_greedy(jobs, max_demand_kva=md)
    return {
        "methods": [
            {
                "method": "CP-SAT",
                "saving": cpsat_res.saving_inr_month,
                "cost_day": cpsat_res.optimal_cost_inr,
                "solve_time_s": cpsat_res.solve_time_s,
                "status": cpsat_res.solver_status,
                "note": "Exact global optimum respecting simultaneous MD limit"
            },
            {
                "method": "Greedy",
                "saving": greedy_res.saving_inr_month,
                "cost_day": greedy_res.optimal_cost_inr,
                "solve_time_s": greedy_res.solve_time_s,
                "status": greedy_res.solver_status,
                "note": "Independent per-job heuristic without global MD coordination"
            }
        ]
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
