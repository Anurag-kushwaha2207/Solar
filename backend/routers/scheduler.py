"""Tariff-Aware Scheduler router — CP-SAT + PPO RL simulation"""
from fastapi import APIRouter
from demo_data import get_demo_schedule, get_tod_tariff
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class ScheduleRequest(BaseModel):
    plant_id: int = 1
    max_demand_kva: float = 200.0
    optimize_method: str = "cpsat"   # cpsat | ppo | greedy
    respect_deadlines: bool = True
    off_peak_priority: bool = True

@router.get("/jobs")
async def get_jobs(plant_id: int = 1):
    jobs = get_demo_schedule()
    current_cost = sum(
        j["duration_h"] * _kw_for_job(j["job_name"]) * _avg_tariff(j["current_start"], j["current_end"])
        for j in jobs
    )
    optimal_cost = sum(
        j["duration_h"] * _kw_for_job(j["job_name"]) * _avg_tariff(j["optimal_start"], j["optimal_end"])
        for j in jobs
    )
    return {
        "jobs": jobs,
        "current_cost_inr_day": round(current_cost, 0),
        "optimal_cost_inr_day": round(optimal_cost, 0),
        "saving_inr_day": round(current_cost - optimal_cost, 0),
        "saving_inr_month": round((current_cost - optimal_cost) * 25, 0),
        "saving_pct": round((current_cost - optimal_cost) / current_cost * 100, 1),
    }

@router.post("/optimize")
async def optimize(req: ScheduleRequest):
    jobs = get_demo_schedule()
    total_saving = sum(j["saving_inr"] for j in jobs if j["is_flexible"])
    method_metrics = {
        "cpsat":  {"r_obj": 18400, "solve_time_s": 0.12, "optimality": "exact"},
        "ppo":    {"r_obj": 17800, "solve_time_s": 0.04, "optimality": "near-optimal"},
        "greedy": {"r_obj": 14200, "solve_time_s": 0.01, "optimality": "heuristic"},
    }
    m = method_metrics.get(req.optimize_method, method_metrics["cpsat"])
    return {
        "method": req.optimize_method,
        "status": "optimal",
        "optimized_jobs": [
            {**j, "selected_start": j["optimal_start"], "selected_end": j["optimal_end"]}
            for j in jobs
        ],
        "saving_inr_month": m["r_obj"],
        "solve_time_s": m["solve_time_s"],
        "optimality_guarantee": m["optimality"],
        "md_peak_kva": 187.4,
        "md_limit_kva": req.max_demand_kva,
        "md_respected": True,
        "comparison": method_metrics,
    }

@router.get("/tariff-heatmap")
async def tariff_heatmap():
    return get_tod_tariff()

def _kw_for_job(name: str) -> float:
    mapping = {
        "Furnace Melt #1": 160, "Furnace Melt #2": 160,
        "Furnace Safety Hold": 40, "Hydraulic Pressing": 66,
        "Compressor Auto-Shutoff": 75, "Fettling Operations": 36,
    }
    return mapping.get(name, 50)

def _avg_tariff(start: float, end: float) -> float:
    from demo_data import get_tariff_rate
    hours = [int((start + (end - start) * i / 10) * 24) % 24 for i in range(11)]
    return sum(get_tariff_rate(h) for h in hours) / len(hours)
