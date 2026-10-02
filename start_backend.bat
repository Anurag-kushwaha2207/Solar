@echo off
echo ========================================================
echo        Starting UrjaMind Backend API (FastAPI)
echo        URL: http://localhost:8000
echo        Docs: http://localhost:8000/api/docs
echo ========================================================
cd /d "%~dp0backend"
python -m uvicorn main:app --reload --port 8000
pause
