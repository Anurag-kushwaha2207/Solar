"""
Database setup — SQLite (dev) / PostgreSQL (prod)
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./urjamind.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ──────────────────────────────────────────────────────────────────

class Plant(Base):
    __tablename__ = "plants"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    industry    = Column(String)          # foundry, textile, ceramics…
    location    = Column(String)
    discom      = Column(String)
    state       = Column(String)
    contract_kva= Column(Float)           # MD contract kVA
    created_at  = Column(DateTime, default=datetime.utcnow)


class EnergyReading(Base):
    __tablename__ = "energy_readings"
    id          = Column(Integer, primary_key=True, index=True)
    plant_id    = Column(Integer, index=True)
    timestamp   = Column(DateTime, index=True)
    total_kw    = Column(Float)
    total_kwh   = Column(Float)
    power_factor= Column(Float)
    kva         = Column(Float)
    interval_min= Column(Integer, default=30)


class MonthlyBill(Base):
    __tablename__ = "monthly_bills"
    id              = Column(Integer, primary_key=True, index=True)
    plant_id        = Column(Integer, index=True)
    month           = Column(String)      # "2026-09"
    total_kwh       = Column(Float)
    total_kvah      = Column(Float)
    max_demand_kva  = Column(Float)
    avg_power_factor= Column(Float)
    tod_peak_kwh    = Column(Float)
    tod_offpeak_kwh = Column(Float)
    total_amount_inr= Column(Float)
    pf_penalty_inr  = Column(Float)
    md_penalty_inr  = Column(Float)


class ProductionLog(Base):
    __tablename__ = "production_logs"
    id          = Column(Integer, primary_key=True, index=True)
    plant_id    = Column(Integer, index=True)
    date        = Column(String)
    shift       = Column(String)          # A / B / C
    product     = Column(String)
    quantity_kg = Column(Float)
    units_produced= Column(Float)


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"
    id              = Column(Integer, primary_key=True, index=True)
    plant_id        = Column(Integer, index=True)
    detected_at     = Column(DateTime, default=datetime.utcnow)
    machine         = Column(String)
    alert_type      = Column(String)      # idle_waste / pf_drop / degradation
    severity        = Column(String)      # high / medium / low
    description     = Column(Text)
    potential_saving= Column(Float)
    resolved        = Column(Boolean, default=False)


class ScheduleJob(Base):
    __tablename__ = "schedule_jobs"
    id              = Column(Integer, primary_key=True, index=True)
    plant_id        = Column(Integer, index=True)
    job_name        = Column(String)
    machine         = Column(String)
    duration_hours  = Column(Float)
    deadline        = Column(String)
    priority        = Column(Integer)
    current_start   = Column(Float)   # fraction of day 0–1
    current_end     = Column(Float)
    optimal_start   = Column(Float)
    optimal_end     = Column(Float)
    is_flexible     = Column(Boolean, default=True)
    saving_inr      = Column(Float)


# ── Init ────────────────────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
