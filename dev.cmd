@echo off
echo Starting GLM Usage Monitor Development Servers...
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8000"
start "Frontend - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"
echo Backend and Frontend windows started.
