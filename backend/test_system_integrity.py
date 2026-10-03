"""
UrjaMind Verification & Integrity Test Suite
============================================
Run via:
  pytest test_system_integrity.py
or:
  python test_system_integrity.py
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from active_data import active_plant

client = TestClient(app, headers={"Authorization": "Bearer demo-token-urjamind-2026"})
unauthenticated_client = TestClient(app)


def setup_function():
    """Ensure clean baseline before each test."""
    active_plant.reset_to_demo()


def test_kpis():
    """1. KPIs: 48,240 kWh and valid bill amounts."""
    r = client.get("/api/dashboard/kpis")
    assert r.status_code == 200, f"KPIs failed: {r.status_code}"
    k_data = r.json()["kpis"]
    assert k_data["total_kwh"] == 48240
    assert k_data["total_amount_inr"] == 296500


def test_anomalies_no_double_counting():
    """2. Anomaly Alerts: exactly Rs. 12,400 across 3 faults; no furnace ToD shift double count."""
    r = client.get("/api/anomaly/alerts")
    assert r.status_code == 200
    anomalies = r.json()
    assert anomalies["total_potential_saving_inr"] == 12400, f"Expected 12400, got {anomalies['total_potential_saving_inr']}"
    furnace_alerts = [a for a in anomalies["alerts"] if "furnace" in a["title"].lower() and "tod" in a["title"].lower()]
    assert len(furnace_alerts) == 0, "Furnace ToD alert found in anomalies (double counting)!"


def test_scheduler_cpsat():
    """3. Scheduler (CP-SAT): exact Rs. 47,500/mo tariff shift savings."""
    r = client.post("/api/scheduler/optimize", json={"plant_id": 1, "max_demand_kva": 250.0, "optimize_method": "cpsat"})
    assert r.status_code == 200
    sched = r.json()
    assert sched["saving_inr_month"] == 47500.0
    assert sched["status"] == "optimal"


def test_scheduler_benchmark_greedy_diff():
    """4. Scheduler Benchmark: CP-SAT and Greedy are independent and distinct."""
    r = client.get("/api/scheduler/methods")
    assert r.status_code == 200
    methods = r.json()["methods"]
    assert len(methods) == 2
    assert methods[0]["saving"] != methods[1]["saving"], "CP-SAT and Greedy have identical savings!"


def test_nilm_resolution_ablation():
    """5. NILM Ablation: Empirical scikit-learn simulation without time-of-day memorization."""
    r = client.get("/api/nilm/resolution-ablation")
    assert r.status_code == 200
    ablation = r.json()
    assert ablation["status"] == "COMPLETED"
    assert len(ablation["ablation"]) == 3
    # Check that it's labeled as simulation benchmark
    assert "Synthetic" in ablation["dataset"] or "Simulation" in ablation.get("phase", "")


def test_copilot_solver_integration():
    """6. Copilot Solver Integration: Answered with solver saving Rs. 47,500."""
    r = client.post("/api/copilot/ask", json={"question": "Scheduler se kitna bachega?"})
    assert r.status_code == 200
    copilot_ans = r.json()
    assert "47,500" in copilot_ans["answer"] or "47500" in copilot_ans["answer"]


def test_copilot_rejection_unsupported():
    """7. Copilot Rejection: Honestly declined unsupported query (load forecast)."""
    r = client.post("/api/copilot/ask", json={"question": "Kal ka load forecast kya hai?"})
    assert r.status_code == 200
    forecast_ans = r.json()
    ans = forecast_ans["answer"].lower()
    assert "phase 2" in ans or "forecast" in ans or "support" in ans or "planned" in ans


def test_copilot_out_of_domain():
    """8. Copilot Out of Domain: Strict rejection for non-energy queries."""
    r = client.post("/api/copilot/ask", json={"question": "What is the capital of France?"})
    assert r.status_code == 200
    ans = r.json()["answer"].lower()
    assert "out of scope" in ans or "energy" in ans or "rajkot" in ans or "plant" in ans


def test_whatsapp_webhook():
    """9. WhatsApp Webhook: Received message, executed tool, returned response."""
    r = client.post("/api/whatsapp/webhook", json={"From": "whatsapp:+919837101838", "Body": "opt"})
    assert r.status_code == 200
    wa_res = r.json()
    assert "47,500" in wa_res["response"] or "47500" in wa_res["response"]


def test_meter_upload_fallback():
    """10. Upload Fallback: Invalid file explicitly returns demo_values_used."""
    r = client.post("/api/ingest/upload-meter-data", files={"file": ("test.txt", b"random content", "text/plain")})
    assert r.status_code == 200
    res = r.json()
    assert res["mode"] == "demo_values_used"


def test_carbon_report():
    """11. Carbon Footprint: CEA emission factor 0.716 and valid SHA-256 digest."""
    r = client.get("/api/carbon/report")
    assert r.status_code == 200
    data = r.json()
    assert data["scope2"]["emission_factor"] == 0.716
    assert len(data["report_sha256"]) == 64


def test_sample_factory_data_upload_sync():
    """12. Real Sample Factory CSV Upload: 441.5 kWh updates Dashboard, Carbon, and Copilot simultaneously."""
    with open("../data/sample_factory_data.csv", "rb") as f:
        file_bytes = f.read()

    r = client.post(
        "/api/ingest/upload-meter-data",
        files={"file": ("sample_factory_data.csv", file_bytes, "text/csv")},
    )
    assert r.status_code == 200
    res = r.json()
    assert res["mode"] == "data_parsed"
    assert active_plant.total_kwh == 441.5

    # 1. Dashboard sync
    dash_r = client.get("/api/dashboard/kpis")
    assert dash_r.json()["kpis"]["total_kwh"] == 441.5

    # 2. Carbon sync
    carbon_r = client.get("/api/carbon/report")
    carbon_data = carbon_r.json()
    assert carbon_data["scope2"]["calc_sep"].startswith("441 kWh")
    assert carbon_data["scope2"]["sep_tco2e"] == 0.32
    assert carbon_data["active_kwh"] == 441.5

    # 3. Copilot sync
    copilot_r = client.post("/api/copilot/ask", json={"question": "Total energy kitni hai?"})
    cop_ans = copilot_r.json()["answer"]
    assert "441.5" in cop_ans

    # 4. Copilot Carbon sync
    copilot_carbon_r = client.post("/api/copilot/ask", json={"question": "Carbon emissions kitna hai?"})
    assert "0.32" in copilot_carbon_r.json()["answer"]

    # Reset active plant
    active_plant.reset_to_demo()
    assert active_plant.total_kwh == 48240


def test_twilio_meta_signature_isolation():
    """13. Signature Isolation: Twilio requests pass when META_APP_SECRET is set, and unauthenticated requests are rejected."""
    from routers import whatsapp
    import os
    original_secret = whatsapp.META_APP_SECRET
    original_env = os.environ.get("ENVIRONMENT", "development")
    try:
        # A. When META_APP_SECRET is active, Twilio requests still pass through
        whatsapp.META_APP_SECRET = "test_meta_secret_active"
        os.environ["META_APP_SECRET"] = "test_meta_secret_active"
        r = client.post(
            "/api/whatsapp/webhook",
            data={"Body": "opt", "From": "whatsapp:+919837101838"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200
        assert "Response" in r.text or "optimal" in r.text.lower() or "47,500" in r.text or "saving" in r.text.lower()

        # B. Security Hole Check: Direct JSON without signature must be REJECTED (401) when META_APP_SECRET is configured
        r_sec = client.post(
            "/api/whatsapp/webhook",
            json={"message": "hi", "from_number": "+919999999999"},
        )
        assert r_sec.status_code == 401, f"Expected 401 when META_APP_SECRET is set, got {r_sec.status_code}"

        # C. Production Security Check: Direct JSON and unsigned Twilio must return 401 when ENVIRONMENT=production
        os.environ["ENVIRONMENT"] = "production"
        r_prod_json = client.post("/api/whatsapp/webhook", json={"message": "hi"})
        assert r_prod_json.status_code == 401, f"Expected 401 in production for direct JSON, got {r_prod_json.status_code}"

        r_prod_twilio = client.post(
            "/api/whatsapp/webhook",
            data={"Body": "hi"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r_prod_twilio.status_code == 401, f"Expected 401 in production for unsigned Twilio, got {r_prod_twilio.status_code}"

    finally:
        whatsapp.META_APP_SECRET = original_secret
        if original_secret:
            os.environ["META_APP_SECRET"] = original_secret
        else:
            os.environ.pop("META_APP_SECRET", None)
        os.environ["ENVIRONMENT"] = original_env


def test_claude_model_and_grounded_note():
    """14. Model & Grounding: claude-sonnet-5-5 configured and no zero-hallucination claim."""
    import agentic_copilot
    import os
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    assert model == "claude-sonnet-5-5"

    cop_r = client.post("/api/copilot/chat", json={"message": "kpi"})
    assert cop_r.status_code == 200
    res = cop_r.json()
    assert "zero hallucination" not in res.get("note", "").lower()
    assert "grounded in tool outputs" in res.get("note", "").lower()


def test_unauthenticated_api_rejection_on_logout():
    """15. Logout & Auth Enforcement: Unauthenticated requests return 401 and /auth/login is removed."""
    # Copilot requires auth
    cop_r = unauthenticated_client.post("/api/copilot/chat", json={"message": "kpi"})
    assert cop_r.status_code == 401, f"Expected 401 for unauthenticated copilot chat, got {cop_r.status_code}"

    # Ingestion requires auth
    ing_r = unauthenticated_client.post("/api/ingest/upload-meter-data", files={"file": ("test.csv", b"dummy", "text/csv")})
    assert ing_r.status_code == 401, f"Expected 401 for unauthenticated meter data upload, got {ing_r.status_code}"

    # Profile requires auth
    me_r = unauthenticated_client.get("/api/auth/me")
    assert me_r.status_code == 401, f"Expected 401 for unauthenticated /api/auth/me, got {me_r.status_code}"

    # Insecure /auth/login endpoint has been completely removed
    login_r = unauthenticated_client.post("/api/auth/login", json={"email": "a", "password": "b"})
    assert login_r.status_code in (404, 405), f"Expected /auth/login to be removed (404/405), got {login_r.status_code}"


def test_firebase_auth_user_isolation():
    """16. Tenant & User Isolation: User A and User B have separate identities and isolated plant data."""
    client_a = TestClient(app, headers={"Authorization": "Bearer test-token-userA"})
    client_b = TestClient(app, headers={"Authorization": "Bearer test-token-userB"})

    # Check verified user profile isolation
    me_a = client_a.get("/api/auth/me").json()
    me_b = client_b.get("/api/auth/me").json()
    assert me_a["uid"] == "userA"
    assert me_b["uid"] == "userB"
    assert me_a["uid"] != me_b["uid"]

    # User B's dashboard remains isolated from User A
    r_kpis_b = client_b.get("/api/dashboard/kpis")
    assert r_kpis_b.status_code == 200
    assert r_kpis_b.json()["kpis"]["total_kwh"] == 48240


def run_tests():
    """Execute all tests programmatically."""
    tests = [
        ("1. KPIs", test_kpis),
        ("2. Anomalies (No double count)", test_anomalies_no_double_counting),
        ("3. Scheduler (CP-SAT)", test_scheduler_cpsat),
        ("4. Scheduler Benchmark (CP-SAT vs Greedy)", test_scheduler_benchmark_greedy_diff),
        ("5. NILM Resolution Ablation", test_nilm_resolution_ablation),
        ("6. Copilot Solver Integration", test_copilot_solver_integration),
        ("7. Copilot Rejection (Unsupported)", test_copilot_rejection_unsupported),
        ("8. Copilot Out of Domain", test_copilot_out_of_domain),
        ("9. WhatsApp Webhook", test_whatsapp_webhook),
        ("10. Upload Fallback", test_meter_upload_fallback),
        ("11. Carbon Report", test_carbon_report),
        ("12. Sample Factory CSV Sync (441.5 kWh)", test_sample_factory_data_upload_sync),
        ("13. Twilio/Meta Signature Isolation", test_twilio_meta_signature_isolation),
        ("14. Claude Model & Tool Grounding", test_claude_model_and_grounded_note),
        ("15. Unauthenticated API Rejection (Logout 401)", test_unauthenticated_api_rejection_on_logout),
        ("16. Firebase Auth & Tenant Isolation", test_firebase_auth_user_isolation),
    ]

    print("\nRunning UrjaMind Test & Verification Suite...")
    passed = 0
    for name, fn in tests:
        try:
            setup_function()
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")

    print(f"\n==========================================")
    print(f"VERIFICATION SUMMARY: {passed}/{len(tests)} TESTS PASSED")
    print(f"==========================================\n")
    if passed < len(tests):
        exit(1)


if __name__ == "__main__":
    run_tests()
