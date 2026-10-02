from cpsat_scheduler import solve_both, ORTOOLS_AVAILABLE, DEMO_JOBS

print(f"OR-Tools available: {ORTOOLS_AVAILABLE}")
both = solve_both()
cpsat  = both["cpsat"]
greedy = both["greedy"]

print(f"\n=== CP-SAT ===")
print(f"Status:        {cpsat.solver_status}")
print(f"Solve time:    {cpsat.solve_time_s}s")
print(f"Current cost:  INR {cpsat.current_cost_inr}/day")
print(f"Optimal cost:  INR {cpsat.optimal_cost_inr}/day")
print(f"Saving/day:    INR {cpsat.saving_inr_day}")
print(f"Saving/month:  INR {cpsat.saving_inr_month}  ({cpsat.saving_pct}%)")
print(f"Energy/day:    {cpsat.energy_kwh_day} kWh  (x26 = {cpsat.energy_kwh_day*26:.0f} kWh)")
print()
for j in cpsat.jobs:
    print(f"  {j['job_name']:30s}  {j['current_start_h']} -> {j['optimal_start_h']}  "
          f"  {j['tariff_shift']:30s}  save INR {j['saving_inr']:7.1f}  "
          f"  ({j['duration_kwh']} kWh)")

print(f"\n=== Greedy ===")
print(f"Saving/month:  INR {greedy.saving_inr_month}  ({greedy.saving_pct}%)")
