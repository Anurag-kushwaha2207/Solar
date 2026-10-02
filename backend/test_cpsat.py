from cpsat_scheduler import solve_cpsat, ORTOOLS_AVAILABLE, DEMO_JOBS
print('OR-Tools available:', ORTOOLS_AVAILABLE)
result = solve_cpsat()
print('Method:', result.method)
print('Status:', result.solver_status)
print('Solve time:', result.solve_time_s, 's')
print('Current cost/day: INR', result.current_cost_inr)
print('Optimal cost/day: INR', result.optimal_cost_inr)
print('Monthly saving: INR', result.saving_inr)
print('Saving pct:', result.saving_pct, '%')
print()
for j in result.jobs:
    name = j['job_name']
    cs   = j['current_start_h']
    os_  = j['optimal_start_h']
    ts   = j['tariff_shift']
    sv   = j['job_saving_inr']
    print(f'  {name:30s}: {cs} -> {os_} | {ts} | Save INR {sv}')
