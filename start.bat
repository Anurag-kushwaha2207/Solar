@echo off
echo.
echo  ⚡ UrjaMind — Starting Full Stack...
echo  ══════════════════════════════════════
echo.

:: Backend
echo  [1/2] Starting FastAPI Backend (port 8000)...
start "UrjaMind Backend" cmd /k "cd backend && pip install -r requirements.txt -q && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a bit
timeout /t 4 /nobreak > nul

:: Frontend
echo  [2/2] Starting React Frontend (port 5173)...
start "UrjaMind Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo  ✅ Both services starting!
echo.
echo  Dashboard → http://localhost:5173
echo  API Docs  → http://localhost:8000/api/docs
echo.
pause
