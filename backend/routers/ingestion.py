"""Ingestion router — consistent with constants.py, honest about what OCR does"""
from fastapi import APIRouter, UploadFile, File, Form
from constants import (
    SEP_TOTAL_KWH, SEP_TOTAL_KVAH, SEP_MAX_DEMAND_KVA, SEP_AVG_PF,
    SEP_TOD_PEAK_KWH, SEP_TOD_OFFPEAK_KWH, SEP_TOTAL_AMOUNT_INR, SEP_PF_PENALTY_INR,
)

router = APIRouter()


@router.post("/upload-bill")
async def upload_bill(file: UploadFile = File(...), plant_id: int = Form(1)):
    """
    Bill upload. Phase 1: returns demo values from constants.py.
    Phase 2: pdfplumber regex + PaddleOCR for image bills.
    """
    content = await file.read()
    return {
        "status": "success",
        "phase": "Phase 1 — demo values (real OCR in Phase 2)",
        "file": file.filename,
        "size_kb": round(len(content) / 1024, 1),
        "ocr_engine": "NOT YET INTEGRATED (Phase 2)",
        "extracted": {
            "month":             "Sep 2026",
            "total_kwh":         SEP_TOTAL_KWH,
            "total_kvah":        SEP_TOTAL_KVAH,
            "max_demand_kva":    SEP_MAX_DEMAND_KVA,
            "power_factor":      SEP_AVG_PF,
            "tod_peak_kwh":      SEP_TOD_PEAK_KWH,
            "tod_offpeak_kwh":   SEP_TOD_OFFPEAK_KWH,
            "total_amount_inr":  SEP_TOTAL_AMOUNT_INR,
            "pf_penalty_inr":    SEP_PF_PENALTY_INR,
        },
        "data_tier": 1,
        "note": "Values are demo constants — real bill parsing via OCR is Phase 2.",
    }


@router.post("/upload-meter-data")
async def upload_meter_data(file: UploadFile = File(...), plant_id: int = Form(1)):
    content = await file.read()
    rows = max(1, len(content.decode(errors="ignore").splitlines()) - 1)
    return {
        "status": "success",
        "file": file.filename,
        "rows_detected": rows,
        "interval_min": 15,
        "date_range": "2026-09-01 to 2026-09-30",
        "data_tier": 2,
        "note": "File received but not yet processed by ML pipeline (Phase 2). Using demo data.",
    }


@router.post("/upload-production")
async def upload_production(file: UploadFile = File(...), plant_id: int = Form(1)):
    content = await file.read()
    return {
        "status": "success",
        "file": file.filename,
        "days_detected": 30,
        "total_production_kg": 12_580,
        "shifts": ["A (6AM-2PM)", "B (2PM-10PM)"],
        "note": "Demo values — real CSV parsing in Phase 2.",
    }


@router.post("/upload-equipment")
async def upload_equipment(file: UploadFile = File(...), plant_id: int = Form(1)):
    return {
        "status": "success",
        "file": file.filename,
        "machines_detected": 5,
        "total_installed_kw": 355,
        "machines": [
            {"name": "Induction Furnace (500 kg)", "rated_kw": 160, "qty": 1},
            {"name": "Air Compressor",              "rated_kw":  75, "qty": 1},
            {"name": "Hydraulic Press",             "rated_kw":  22, "qty": 3},
            {"name": "Fettling Machine",            "rated_kw":   6, "qty": 6},
            {"name": "Lighting & HVAC",             "rated_kw":  18, "qty": 1},
        ],
        "note": "Demo values — real equipment register parser in Phase 2.",
    }


@router.post("/load-demo")
async def load_demo(plant_id: int = 1):
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
        "period": "Sep 2026",
        "note": "Demo data loaded from constants.py. All values are consistent.",
        "message": "✅ Demo data loaded. Navigate to Dashboard.",
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
