from fastapi import FastAPI, File, HTTPException, UploadFile

from .analytics import compute_carbon, detect_anomalies, generate_schedule, get_energy_summary
from .data_loader import load_csv_from_bytes, load_sample_data

app = FastAPI(title="UrjaMind API", version="1.0.0")


@app.get("/")
def root():
    return {
        "project": "UrjaMind",
        "status": "ok",
        "message": "SME energy intelligence API is running.",
        "endpoints": {
            "health": "/api/health",
            "summary": "/api/summary",
            "anomalies": "/api/anomalies",
            "schedule": "/api/schedule",
            "carbon": "/api/carbon",
            "upload": "/api/upload",
            "docs": "/docs",
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "UrjaMind"}


@app.get("/api/summary")
def summary():
    df = load_sample_data()
    return get_energy_summary(df)


@app.get("/api/anomalies")
def anomalies():
    df = load_sample_data()
    return {"anomalies": detect_anomalies(df)}


@app.get("/api/schedule")
def schedule():
    df = load_sample_data()
    return {"schedule": generate_schedule(df)}


@app.get("/api/carbon")
def carbon():
    df = load_sample_data()
    return compute_carbon(df)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        file_bytes = await file.read()
        df = load_csv_from_bytes(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV data: {exc}") from exc

    return {
        "filename": file.filename,
        "rows": len(df),
        "columns": list(df.columns),
        "summary": get_energy_summary(df),
        "anomalies": detect_anomalies(df),
        "schedule": generate_schedule(df),
        "carbon": compute_carbon(df),
    }
