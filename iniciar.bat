@echo off
rem Arranca backend (puerto 8010) y frontend (puerto 5173) en dos ventanas y abre el navegador.
cd /d "%~dp0"
if not exist backend\.venv (
  echo Falta el entorno de Python. Siga el README: python -m venv .venv ^& pip install -r requirements.txt
  pause & exit /b 1
)
start "Sala STEAM - Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python -m uvicorn app.main:app --port 8010"
start "Sala STEAM - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 8 >nul
start http://localhost:5173
