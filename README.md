# UrjaMind

UrjaMind is a complete prototype for an AI-powered energy intelligence platform built for Indian SMEs. It helps plant managers understand where energy is being lost, diagnose inefficiencies, schedule manufacturing around tariff windows, and generate carbon visibility without needing expensive hardware installation.

## What this project includes

This repository contains:

- a FastAPI backend with energy summary APIs,
- a Streamlit dashboard mockup,
- a sample industrial plant dataset,
- a tariff-aware scheduling and anomaly logic,
- carbon calculation utilities,
- an end-to-end project structure ready for extension.

## Problem it solves

Small and medium manufacturers often have:

- no machine-level energy visibility,
- no clear diagnosis of why electricity cost is rising,
- no scheduling strategy to reduce maximum demand and tariff penalties,
- no buyer-ready carbon data.

UrjaMind solves this using existing plant data instead of requiring new sensors on every machine.

## Project structure

- [README.md](README.md) — project overview and run instructions
- [docs/urjamind-submission.md](docs/urjamind-submission.md) — business and technical submission write-up
- [data/sample_factory_data.csv](data/sample_factory_data.csv) — sample SME energy dataset
- [urjamind/analytics.py](urjamind/analytics.py) — anomaly detection, scheduling, and carbon logic
- [urjamind/api.py](urjamind/api.py) — FastAPI endpoints
- [app/dashboard.py](app/dashboard.py) — Streamlit dashboard
- [main.py](main.py) — backend startup entry point

## Tech stack

- Python
- FastAPI
- Streamlit
- Pandas and NumPy

## Installation

```bash
cd /workspaces/Solar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
cd /workspaces/Solar
source .venv/bin/activate
uvicorn urjamind.api:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- http://localhost:8000/api/health
- http://localhost:8000/api/summary
- http://localhost:8000/api/anomalies
- http://localhost:8000/api/schedule
- http://localhost:8000/api/carbon

## Run the dashboard

```bash
cd /workspaces/Solar
source .venv/bin/activate
streamlit run app/dashboard.py
```

## Example features

- total energy and peak load summary
- anomaly evidence for poor power factor and idle load
- tariff-aware shift suggestions
- carbon estimate using emissions factor
- SME-friendly dashboard layout

Schedule savings are indicative upper bounds: they assume all observed energy
from a higher-tariff shift can move to the lowest-tariff shift without changing
total consumption. Validate job flexibility and production constraints before
acting on a recommendation.

Run the analytics tests with:

```bash
python -m unittest discover -s tests
```

## Use case

A textile, foundry, or ceramics plant can upload its current energy and production data and immediately receive:

- demand and cost diagnosis,
- likely operating inefficiencies,
- shift-based recommendations,
- carbon snapshots for reporting.

## Submission note

This project is built as a practical product prototype, not just a research concept. It demonstrates how an SME can obtain actionable energy intelligence from already available data in a low-friction and scalable manner.
