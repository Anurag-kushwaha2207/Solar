import sys, os
sys.path.insert(0, os.path.abspath('backend'))
from active_data import active_plant
from routers.anomaly import get_alerts
from routers.dashboard import get_kpis, get_baseline_trend, get_load_profile
from routers.carbon import get_report, intensity_trend
from routers.scheduler import get_jobs, compare_methods
from agentic_copilot import ask_agentic_copilot
import asyncio

async def test_all():
    plant = active_plant.get_plant()
    plant.company_name = 'ABC Manufacturing Pvt. Ltd.'
    plant.plant_name = 'ABC Manufacturing Pvt. Ltd.'
    plant.total_kwh = 18450.0
    plant.total_bill_inr = 176450.0
    plant.avg_pf = 0.94
    plant.source = 'uploaded_pdf'
    plant.filename = '01_Electricity_Bill_Dummy.pdf'
    plant.max_demand_kva = 285.0
    plant.contract_kva = 285.0
    plant.production_kg = 1145.0
    plant.specific_energy = 1.24
    plant.machines = {
        'CNC Production Machine #1 (22 kW)': 4515.7,
        'CNC Production Machine #2 (22 kW)': 4515.7,
        'CNC Production Machine #3 (22 kW)': 4515.7,
        'CNC Production Machine #4 (22 kW)': 4515.7,
        'Plant Lighting & Auxiliary Load': 387.2
    }

    print('=== Testing Anomalies ===')
    alerts_res = await get_alerts()
    alerts = alerts_res['alerts']
    print('Total alerts:', len(alerts), 'Total potential saving INR:', alerts_res['total_potential_saving_inr'])
    for a in alerts:
        print(' -', a['title'], 'INR', a['potential_saving_inr'])
        assert 'Compressor' not in a['title'], 'Compressor alert found!'
        assert 'Press' not in a['title'], 'Press alert found!'
        assert '0.87' not in a['title'], 'Foundry PF 0.87 alert found!'

    print('\n=== Testing Dashboard KPIs & Trends ===')
    kpis = await get_kpis()
    print('Units:', kpis['kpis']['total_kwh'], 'Bill:', kpis['kpis']['total_amount_inr'], 'PF:', kpis['kpis']['avg_power_factor'])
    assert kpis['kpis']['total_kwh'] == 18450
    assert kpis['kpis']['avg_power_factor'] == 0.94
    assert kpis['kpis']['pf_penalty_inr'] == 0

    base_trend = await get_baseline_trend()
    print('Baseline unit:', base_trend['unit'], 'Baseline val:', base_trend['baseline_kwh_per_kg'])
    assert base_trend['unit'] == 'kWh/unit'
    assert base_trend['baseline_kwh_per_kg'] == [1.24]

    load_prof = await get_load_profile()
    slots = load_prof['slots']
    first_slot_keys = list(slots[0].keys())
    print('Load profile keys:', first_slot_keys)
    assert any('CNC' in k for k in first_slot_keys)
    assert 'furnace_kw' not in first_slot_keys

    print('\n=== Testing Scheduler ===')
    sched_jobs = await get_jobs()
    job_names = [j['job_name'] for j in sched_jobs['jobs']]
    print('Jobs:', job_names)
    print('Monthly Saving:', sched_jobs['saving_inr_month'], 'Saving Pct:', sched_jobs['saving_pct'])
    assert any('CNC' in j['job_name'] for j in sched_jobs['jobs'])
    assert not any('Furnace' in j['job_name'] for j in sched_jobs['jobs'])
    assert sched_jobs['saving_inr_month'] == 20239.0
    assert round(sched_jobs['saving_pct'], 1) == 11.5

    methods = await compare_methods(285)
    print('Methods:', methods['methods'])
    cpsat_s = [m for m in methods['methods'] if m['method'] == 'CP-SAT'][0]['saving']
    greedy_s = [m for m in methods['methods'] if m['method'] == 'Greedy'][0]['saving']
    print('CP-SAT saving:', cpsat_s, 'Greedy saving:', greedy_s)
    assert cpsat_s == 20239.0
    assert greedy_s > 0

    print('\n=== Testing Carbon ===')
    carb = await get_report()
    print('Scope 1:', carb['scope1']['total_tco2e'], 'Scope 2:', carb['scope2']['total_tco2e'])
    assert carb['scope1']['total_tco2e'] == 0.0
    assert carb['scope2']['total_tco2e'] == 13.21
    tod_mv = [m for m in carb['mv_table'] if 'ToD' in m['name'] or 'Shift' in m['name']][0]
    print('Carbon ToD saving INR:', tod_mv['saving_inr'])
    assert tod_mv['saving_inr'] == 20239.0
    assert not any('PF correction' in m['name'] for m in carb['mv_table'])

    print('\n=== Testing Copilot ===')
    q1_res = ask_agentic_copilot('Power factor kya hai?')
    q1 = q1_res.get('content', '')
    print('Copilot PF reply snippet:', q1[:100].encode('ascii', 'replace').decode())
    assert '0.94' in q1
    assert 'healthy' in q1.lower() or 'no penalty' in q1.lower()
    assert '0.87' not in q1

    q2_res = ask_agentic_copilot('Bill kyun badha?')
    q2 = q2_res.get('content', '')
    print('Copilot Bill reply snippet:', q2[:100].encode('ascii', 'replace').decode())
    assert '18,450' in q2 or '18450' in q2
    assert '176,450' in q2 or '176450' in q2

    print('\n>>> ALL 6 REQUIREMENT CATEGORIES FULLY VERIFIED AND MATCHING 100%! <<<')

asyncio.run(test_all())
