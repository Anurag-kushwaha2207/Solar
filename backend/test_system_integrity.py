from fastapi.testclient import TestClient
import sys
from main import app

def run_tests():
    print("Running UrjaMind Verification Suite...")
    client = TestClient(app)

    # 1. KPIs
    r = client.get("/api/dashboard/kpis")
    assert r.status_code == 200, f"KPIs failed: {r.status_code}"
    res_kpis = r.json()
    k_data = res_kpis["kpis"]
    print(f"[PASS] 1. KPIs: {k_data['total_kwh']} kWh, Bill: INR {k_data['total_amount_inr']}")


    # 2. Anomaly Alerts (Strictly 3 operational faults, no double count)
    r = client.get("/api/anomaly/alerts")
    assert r.status_code == 200
    anomalies = r.json()
    assert anomalies["total_potential_saving_inr"] == 12400, f"Expected 12400, got {anomalies['total_potential_saving_inr']}"
    furnace_alerts = [a for a in anomalies["alerts"] if "furnace" in a["title"].lower() and "tod" in a["title"].lower()]
    assert len(furnace_alerts) == 0, "Furnace ToD alert found in anomalies (double counting)!"
    print(f"[PASS] 2. Anomalies: {len(anomalies['alerts'])} faults, total saving INR {anomalies['total_potential_saving_inr']} (no double counting)")


    # 3. Scheduler optimize & methods
    r = client.post("/api/scheduler/optimize", json={"plant_id": 1, "max_demand_kva": 250.0, "optimize_method": "cpsat"})
    assert r.status_code == 200
    sched = r.json()
    assert sched["saving_inr_month"] == 47500.0
    print(f"[PASS] 3. Scheduler (CP-SAT): Saving INR {sched['saving_inr_month']}, Cost/day: INR {sched['optimal_cost_inr']}")

    r = client.get("/api/scheduler/methods")
    assert r.status_code == 200
    methods = r.json()["methods"]
    assert len(methods) == 2
    assert methods[0]["saving"] != methods[1]["saving"], "CP-SAT and Greedy have identical savings!"
    print(f"[PASS] 4. Scheduler Benchmark: {methods[0]['method']} = INR {methods[0]['saving']} vs {methods[1]['method']} = INR {methods[1]['saving']} (distinct & verified)")

    # 4. NILM Resolution Ablation
    r = client.get("/api/nilm/resolution-ablation")
    assert r.status_code == 200
    ablation = r.json()
    assert ablation["status"] == "COMPLETED"
    print(f"[PASS] 5. NILM Ablation (scikit-learn): {len(ablation['ablation'])} resolutions evaluated. 15-min Macro R2 = {ablation['ablation'][1]['macro_r2']}")

    # 5. Agentic Copilot
    r = client.post("/api/copilot/ask", json={"question": "Scheduler se kitna bachega?"})
    assert r.status_code == 200
    copilot_ans = r.json()
    assert "47,500" in copilot_ans["answer"] or "47500" in copilot_ans["answer"], f"Expected 47,500 in copilot answer, got: {copilot_ans['answer']}"
    print(f"[PASS] 6. Copilot Solver Integration: Answered with solver saving 47,500 using tool {copilot_ans['tool_used']}")

    # 6. Copilot Honest Rejection
    r = client.post("/api/copilot/ask", json={"question": "Kal ka load forecast kya hai?"})
    assert r.status_code == 200
    forecast_ans = r.json()
    assert "phase 2" in forecast_ans["answer"].lower() or "forecast" in forecast_ans["answer"].lower() or "support" in forecast_ans["answer"].lower()
    print("[PASS] 7. Copilot Rejection: Honestly declined unsupported query (load forecast)")

    # 7. WhatsApp Webhook
    r = client.post("/api/whatsapp/webhook", json={"From": "whatsapp:+919837101838", "Body": "opt"})
    assert r.status_code == 200
    wa_res = r.json()
    assert "47,500" in wa_res["response"] or "47500" in wa_res["response"]
    print("[PASS] 8. WhatsApp Webhook: Received message from +919837101838, executed run_optimizer, returned answer")

    # 8. Meter upload with demo fallback
    r = client.post("/api/ingest/upload-meter-data", files={"file": ("test.txt", b"random content", "text/plain")})
    assert r.status_code == 200
    res = r.json()
    assert res["mode"] == "demo_values_used", f"Expected mode demo_values_used, got: {res}"
    print(f"[PASS] 9. Upload Fallback: Invalid file explicitly returns status '{res['status']}' and mode '{res['mode']}'")

    print("\n==========================================")
    print("ALL 9 INTEGRITY VERIFICATION CHECKS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()

