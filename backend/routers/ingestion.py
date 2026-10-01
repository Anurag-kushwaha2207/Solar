"""Data Ingestion router — file upload, OCR simulation, validation"""
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
import random

router = APIRouter()

@router.post("/upload-bill")
async def upload_bill(file: UploadFile = File(...), plant_id: int = Form(1)):
    content = await file.read()
    size_kb = len(content) / 1024
    return {
        "status": "success",
        "file": file.filename,
        "size_kb": round(size_kb, 1),
        "ocr_engine": "PaddleOCR",
        "extracted": {
            "month": "Sep 2026",
            "total_kwh": 48240,
            "total_kvah": 55448,
            "max_demand_kva": 187.4,
            "power_factor": 0.87,
            "tod_peak_kwh": 12860,
            "tod_offpeak_kwh": 18640,
            "total_amount_inr": 298720,
            "pf_penalty_inr": 3200,
        },
        "data_tier": 1,
        "confidence": 0.91,
        "message": "Bill parsed successfully — Tier 1 analysis ready",
    }

@router.post("/upload-meter-data")
async def upload_meter_data(file: UploadFile = File(...), plant_id: int = Form(1)):
    content = await file.read()
    rows = len(content.decode(errors="ignore").splitlines())
    return {
        "status": "success",
        "file": file.filename,
        "rows_detected": rows,
        "interval_min": 15,
        "date_range": "2026-09-01 to 2026-09-30",
        "data_tier": 2,
        "confidence": 0.88,
        "message": f"Interval data loaded — {rows} rows · Tier 2 NILM analysis ready",
    }

@router.post("/upload-production")
async def upload_production(file: UploadFile = File(...), plant_id: int = Form(1)):
    content = await file.read()
    return {
        "status": "success",
        "file": file.filename,
        "days_detected": 30,
        "total_production_kg": 12580,
        "shifts": ["A (6AM-2PM)", "B (2PM-10PM)"],
        "message": "Production log parsed — baseline model will use this",
    }

@router.post("/upload-equipment")
async def upload_equipment(file: UploadFile = File(...), plant_id: int = Form(1)):
    return {
        "status": "success",
        "file": file.filename,
        "machines_detected": 7,
        "total_installed_kw": 355,
        "vfd_machines": 2,
        "message": "Equipment register parsed — digital twin calibrating",
        "machines": [
            {"name": "Induction Furnace", "rated_kw": 160, "qty": 1},
            {"name": "Air Compressor", "rated_kw": 75, "qty": 1},
            {"name": "Hydraulic Press", "rated_kw": 22, "qty": 3},
            {"name": "Fettling Machine", "rated_kw": 6, "qty": 6},
            {"name": "Lighting & HVAC", "rated_kw": 18, "qty": 1},
        ],
    }

@router.post("/load-demo")
async def load_demo(plant_id: int = 1):
    """Load Rajkot Foundry demo dataset instantly."""
    return {
        "status": "success",
        "plant": "Rajkot Precision Foundry Pvt. Ltd.",
        "data_loaded": {
            "monthly_bill": True,
            "interval_data_15min": True,
            "production_log": True,
            "equipment_register": True,
        },
        "data_tier": 2,
        "confidence": 0.88,
        "period": "Sep 2026",
        "message": "✅ Demo data loaded — all 4 data sources ready. Navigate to Dashboard.",
    }

@router.get("/status/{plant_id}")
async def ingestion_status(plant_id: int):
    return {
        "plant_id": plant_id,
        "bill_uploaded": True,
        "meter_data_uploaded": True,
        "production_uploaded": True,
        "equipment_uploaded": True,
        "current_tier": 2,
        "pipeline_status": "complete",
        "last_processed": "2026-09-30T09:16:00",
    }
