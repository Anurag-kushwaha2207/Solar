"""Anomaly Detection router"""
from fastapi import APIRouter
from demo_data import get_demo_anomalies

router = APIRouter()

@router.get("/alerts")
async def get_alerts(plant_id: int = 1, severity: str = None):
    alerts = get_demo_anomalies()
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    total_saving = sum(a["potential_saving_inr"] for a in alerts)
    return {
        "plant_id": plant_id,
        "total_alerts": len(alerts),
        "total_potential_saving_inr": total_saving,
        "model": "LSTM-VAE + CUSUM drift detector",
        "alerts": alerts,
    }

@router.get("/summary")
async def get_summary():
    alerts = get_demo_anomalies()
    return {
        "high": sum(1 for a in alerts if a["severity"] == "high"),
        "medium": sum(1 for a in alerts if a["severity"] == "medium"),
        "low": sum(1 for a in alerts if a["severity"] == "low"),
        "total_saving_inr": sum(a["potential_saving_inr"] for a in alerts),
    }

@router.post("/resolve/{alert_id}")
async def resolve_alert(alert_id: int):
    return {"status": "resolved", "alert_id": alert_id, "message": "Alert marked resolved"}
