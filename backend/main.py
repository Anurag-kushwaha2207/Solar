"""
UrjaMind Backend — FastAPI Application
AI Energy Intelligence Platform for Indian SMEs
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file before importing routers
load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import ingestion, dashboard, nilm, anomaly, scheduler, carbon, copilot, auth, whatsapp
from auth_middleware import get_current_user, get_optional_current_user

app = FastAPI(
    title="UrjaMind API",
    description="AI Energy Intelligence Platform for Indian SMEs — Zero Hardware",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — dynamically read ALLOWED_ORIGINS from environment variable with local fallbacks
_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,       prefix="/api/auth",      tags=["Authentication"])
app.include_router(ingestion.router,  prefix="/api/ingest",    tags=["Data Ingestion"], dependencies=[Depends(get_current_user)])
app.include_router(dashboard.router,  prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(nilm.router,       prefix="/api/nilm",      tags=["NILM Disaggregation"])
app.include_router(anomaly.router,    prefix="/api/anomaly",   tags=["Anomaly Detection"])
app.include_router(scheduler.router,  prefix="/api/scheduler", tags=["Tariff Scheduler"])
app.include_router(carbon.router,     prefix="/api/carbon",    tags=["Carbon Report"])
app.include_router(copilot.router,    prefix="/api/copilot",   tags=["LLM Copilot"],    dependencies=[Depends(get_current_user)])
app.include_router(whatsapp.router,   prefix="/api",           tags=["WhatsApp"])

@app.get("/webhook")

async def root_webhook_get(request: Request):
    from routers.whatsapp import verify_meta_webhook
    return await verify_meta_webhook(
        hub_mode=request.query_params.get("hub.mode"),
        hub_verify_token=request.query_params.get("hub.verify_token"),
        hub_challenge=request.query_params.get("hub.challenge"),
    )

@app.post("/webhook")
async def root_webhook_post(request: Request):
    from routers.whatsapp import receive_whatsapp_message
    return await receive_whatsapp_message(request)


@app.get("/")
@app.get("/api")
async def root():
    return {
        "status": "online",
        "service": "UrjaMind Backend API",
        "version": "1.0.0",
        "message": "⚡ AI Energy Intelligence for Indian SMEs",
        "docs": "/api/docs",
        "health": "/api/health",
        "frontend": "https://urjamind-energy.web.app"
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "UrjaMind API",
        "version": "1.0.0",
        "message": "⚡ AI Energy Intelligence for Indian SMEs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
