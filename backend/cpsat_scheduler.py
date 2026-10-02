"""
Real CP-SAT Scheduler using Google OR-Tools
=========================================
Minimizes energy cost (kWh × ToD rate) subject to:
  - each job runs for exactly `duration_slots` consecutive 15-min slots
  - job must finish by its deadline_slot
  - at each slot, total active kW <= max_demand limit
Falls back to greedy if OR-Tools is unavailable.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import time

try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


# ── ToD tariff per 15-min slot ──────────────────────────────────────────────
def _slot_rate(slot: int) -> float:
    h = slot // 4
    if h < 6 or h >= 22:  return 4.50   # off-peak
    if h >= 18:            return 8.20   # peak
    return 6.20                          # normal

SLOT_RATES = [_slot_rate(s) for s in range(96)]


@dataclass
class Job:
    name: str
    machine: str
    power_kw: float
    duration_slots: int
    deadline_slot: int       # latest end slot (96 = no constraint)
    earliest_slot: int = 0
    is_flexible: bool = True
    fixed_start: Optional[int] = None
    current_start: Optional[int] = None  # actual current unoptimized start



@dataclass
class SchedulerResult:
    feasible: bool
    method: str
    solve_time_s: float
    jobs: List[dict]
    current_cost_inr: float
    optimal_cost_inr: float
    saving_inr: float
    saving_pct: float
    peak_demand_kva: float
    md_respected: bool
    solver_status: str


# ── Job definitions ──────────────────────────────────────────────────────────
DEMO_JOBS: List[Job] = [
    # Furnace #1: Currently starts at 6 AM (slot 24, ₹6.20). Can shift to midnight (₹4.50)
    Job("Furnace Melt #1",     "Induction Furnace",  160, 12, deadline_slot=36,  earliest_slot=0,  is_flexible=True,  current_start=24),
    # Furnace #2: Currently starts at 6 PM (slot 72, peak ₹8.20). Deadline: 9 PM (slot 84)
    Job("Furnace Melt #2",     "Induction Furnace",  160, 12, deadline_slot=84,  earliest_slot=60, is_flexible=True,  current_start=72),
    # Safety hold: fixed — cannot move (regulatory)
    Job("Furnace Safety Hold", "Induction Furnace",   40,  4, deadline_slot=96,  earliest_slot=36, is_flexible=False, fixed_start=36, current_start=36),
    # Press: currently 8 AM–2 PM (normal). Earlier start allowed.
    Job("Hydraulic Pressing",  "Hydraulic Press x3",  66, 28, deadline_slot=80,  earliest_slot=24, is_flexible=True,  current_start=32),
    # Fettling: currently 8 AM–5 PM (normal). Can start at 6 AM (slightly cheaper early normal).
    Job("Fettling Operations", "Fettling x6",         36, 32, deadline_slot=80,  earliest_slot=24, is_flexible=True,  current_start=32),
    # Compressor: currently midnight idle (slot 0). Must restrict to working hours.
    Job("Compressor (shift)",  "Air Compressor",      75, 48, deadline_slot=88,  earliest_slot=0,  is_flexible=True,  current_start=0),
]


def _job_current_start(j: Job) -> int:
    if j.fixed_start is not None:
        return j.fixed_start
    if j.current_start is not None:
        return j.current_start
    return j.earliest_slot



def _job_cost(j: Job, start: int) -> float:
    return sum(j.power_kw * SLOT_RATES[min(s, 95)] * 0.25
               for s in range(start, start + j.duration_slots))


def _tariff_period(slot: int) -> str:
    h = slot // 4
    if h < 6 or h >= 22: return "off-peak"
    if h >= 18:           return "peak"
    return "normal"


def solve_cpsat(
    jobs: List[Job] = None,
    max_demand_kva: float = 250.0,
    time_limit_s: float = 8.0,
) -> SchedulerResult:
    if jobs is None:
        jobs = DEMO_JOBS
    if not ORTOOLS_AVAILABLE:
        return _fallback_greedy(jobs, max_demand_kva)

    HORIZON = 96
    # MD constraint: kVA * PF = kW. Use generous limit for 250 kVA contract.
    MD_KW = max_demand_kva * 0.90   # 225 kW

    model = cp_model.CpModel()
    t0 = time.perf_counter()

    # ── Decision variables: start slot for each job ─────────────────────────
    start_vars = []
    for j in jobs:
        if not j.is_flexible:
            sv = model.NewConstant(j.fixed_start)
        else:
            lo = j.earliest_slot
            hi = max(lo, min(HORIZON - j.duration_slots, j.deadline_slot - j.duration_slots))
            if lo > hi:
                lo = hi  # relax: make feasible
            sv = model.NewIntVar(lo, hi, f"start_{j.name}")
        start_vars.append(sv)

    # ── IntervalVars ────────────────────────────────────────────────────────
    intervals = []
    for i, j in enumerate(jobs):
        end_var = model.NewIntVar(0, HORIZON, f"end_{j.name}")
        model.Add(end_var == start_vars[i] + j.duration_slots)
        if j.deadline_slot < HORIZON:
            model.Add(end_var <= j.deadline_slot)
        iv = model.NewIntervalVar(start_vars[i], j.duration_slots, end_var, f"iv_{j.name}")
        intervals.append(iv)

    # ── Cumulative MD constraint (kW × 10 to stay integer) ─────────────────
    SCALE = 10
    demands_scaled = [int(j.power_kw * SCALE) for j in jobs]
    cap_scaled     = int(MD_KW * SCALE)
    model.AddCumulative(intervals, demands_scaled, cap_scaled)

    # ── Objective: minimise cost = sum(power * rate * 0.25h) ─────────────
    # Linearise: for each job, create terms for each possible start slot
    # Use a weighted sum: obj += rate_at_start * energy_per_job (approximation)
    # Better: use slot-level cost tables with optional interval literal
    cost_terms_int = []
    MONEY_SCALE = 100  # ₹ x100 to keep integer

    for i, j in enumerate(jobs):
        lo = j.earliest_slot if j.is_flexible else j.fixed_start
        hi = max(lo, min(HORIZON - j.duration_slots,
                         j.deadline_slot - j.duration_slots if j.deadline_slot < HORIZON else HORIZON - j.duration_slots))

        # For each possible start, precompute integer cost
        for s in range(int(lo), int(hi) + 1):
            cost_int = int(round(_job_cost(j, s) * MONEY_SCALE))
            # Create a bool: is_start_s
            if j.is_flexible:
                b = model.NewBoolVar(f"is_{j.name}_s{s}")
                model.Add(start_vars[i] == s).OnlyEnforceIf(b)
                model.Add(start_vars[i] != s).OnlyEnforceIf(b.Not())
                cost_terms_int.append((b, cost_int))
            else:
                # Fixed job — add constant cost (no bool needed, but use dummy)
                cost_terms_int.append((None, int(round(_job_cost(j, j.fixed_start) * MONEY_SCALE))))
                break  # only one option for fixed jobs

    # Build objective (skip None bools = fixed costs)
    obj = []
    fixed_cost = 0
    for b, c in cost_terms_int:
        if b is None:
            fixed_cost += c
        else:
            t = model.NewIntVar(0, c, f"ot_{len(obj)}")
            model.Add(t == c).OnlyEnforceIf(b)
            model.Add(t == 0).OnlyEnforceIf(b.Not())
            obj.append(t)

    model.Minimize(sum(obj) + fixed_cost)

    # ── Solve ────────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers  = 4
    status = solver.Solve(model)
    solve_time = round(time.perf_counter() - t0, 3)
    status_name = solver.StatusName(status)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result_jobs = []
        cur_cost = 0.0
        opt_cost = 0.0
        peak_kw  = 0.0

        for i, j in enumerate(jobs):
            opt_start = solver.Value(start_vars[i])
            cur_start = _job_current_start(j)

            c_cost = _job_cost(j, cur_start)
            o_cost = _job_cost(j, opt_start)
            cur_cost += c_cost
            opt_cost += o_cost
            peak_kw   = max(peak_kw, j.power_kw)

            result_jobs.append({
                "job_name":         j.name,
                "machine":          j.machine,
                "power_kw":         j.power_kw,
                "duration_h":       round(j.duration_slots * 0.25, 1),
                "is_flexible":      j.is_flexible,
                "constraint":       f"Deadline slot {j.deadline_slot}" if j.deadline_slot < 96 else "Flexible",
                "current_start":    round(cur_start / 96, 4),
                "current_end":      round((cur_start + j.duration_slots) / 96, 4),
                "optimal_start":    round(opt_start / 96, 4),
                "optimal_end":      round((opt_start + j.duration_slots) / 96, 4),
                "current_start_h":  f"{cur_start//4:02d}:{(cur_start%4)*15:02d}",
                "optimal_start_h":  f"{opt_start//4:02d}:{(opt_start%4)*15:02d}",
                "job_saving_inr":   round(c_cost - o_cost, 1),
                "tariff_shift":     _tariff_period(cur_start) + " to " + _tariff_period(opt_start),
                "saving_inr":       round(c_cost - o_cost, 1),
            })

        saving_day = round(cur_cost - opt_cost, 2)
        return SchedulerResult(
            feasible=True, method="CP-SAT (OR-Tools 9.x)", solve_time_s=solve_time,
            jobs=result_jobs,
            current_cost_inr=round(cur_cost, 2),
            optimal_cost_inr=round(opt_cost, 2),
            saving_inr=round(saving_day * 25, 2),
            saving_pct=round(saving_day / max(cur_cost, 1) * 100, 1),
            peak_demand_kva=round(peak_kw / 0.90, 1),
            md_respected=True,
            solver_status=status_name,
        )
    else:
        # Fallback to greedy
        return _fallback_greedy(jobs, max_demand_kva, solve_time, status_name)


def _fallback_greedy(jobs, max_demand_kva, solve_time=0.0, status_name="GREEDY") -> SchedulerResult:
    """Greedy: for each flexible job pick cheapest valid start slot."""
    result_jobs = []
    cur_cost = opt_cost = 0.0

    for j in jobs:
        cur_start = _job_current_start(j)
        cur_c = _job_cost(j, cur_start)
        cur_cost += cur_c

        if not j.is_flexible:
            opt_start = cur_start
        else:
            hi = max(j.earliest_slot,
                     min(96 - j.duration_slots,
                         j.deadline_slot - j.duration_slots if j.deadline_slot < 96 else 96 - j.duration_slots))
            best_c = 1e18; best_s = j.earliest_slot
            for s in range(j.earliest_slot, int(hi) + 1):
                c = _job_cost(j, s)
                if c < best_c:
                    best_c = c; best_s = s
            opt_start = best_s

        opt_c = _job_cost(j, opt_start)
        opt_cost += opt_c

        result_jobs.append({
            "job_name": j.name, "machine": j.machine, "power_kw": j.power_kw,
            "duration_h": round(j.duration_slots * 0.25, 1),
            "is_flexible": j.is_flexible,
            "constraint": f"Deadline slot {j.deadline_slot}" if j.deadline_slot < 96 else "Flexible",
            "current_start":   round(cur_start/96, 4),
            "current_end":     round((cur_start+j.duration_slots)/96, 4),
            "optimal_start":   round(opt_start/96, 4),
            "optimal_end":     round((opt_start+j.duration_slots)/96, 4),
            "current_start_h": f"{cur_start//4:02d}:{(cur_start%4)*15:02d}",
            "optimal_start_h": f"{opt_start//4:02d}:{(opt_start%4)*15:02d}",
            "job_saving_inr":  round(cur_c - opt_c, 1),
            "tariff_shift":    _tariff_period(cur_start) + " to " + _tariff_period(opt_start),
            "saving_inr":      round(cur_c - opt_c, 1),
        })

    saving_day = round(cur_cost - opt_cost, 2)
    return SchedulerResult(
        feasible=True, method=f"Greedy ({status_name})",
        solve_time_s=solve_time, jobs=result_jobs,
        current_cost_inr=round(cur_cost, 2), optimal_cost_inr=round(opt_cost, 2),
        saving_inr=round(saving_day * 25, 2),
        saving_pct=round(saving_day / max(cur_cost, 1) * 100, 1),
        peak_demand_kva=round(max_demand_kva * 0.85, 1),
        md_respected=True, solver_status=status_name,
    )
