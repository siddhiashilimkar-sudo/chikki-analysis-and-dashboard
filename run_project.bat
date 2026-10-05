@echo off
setlocal
cd /d "%~dp0"
set PIP_CACHE_DIR=%~dp0.pip-cache
if not exist .venv\Scripts\python.exe python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
python -c "from sqlalchemy import create_engine" >nul 2>&1
if errorlevel 1 (
  echo Retrying SQLAlchemy without native extensions for Windows application-control compatibility...
  set DISABLE_SQLALCHEMY_CEXT=1
  pip uninstall -y SQLAlchemy
  pip install --no-binary=SQLAlchemy "SQLAlchemy>=2.0"
)
if not exist data\raw\business_data.xlsx python scripts\generate_demo_data.py
python scripts\setup_database.py
python etl\pipeline.py
if errorlevel 1 pause
start "Maganlal BI API" powershell -NoExit -Command "Set-Location -LiteralPath '%~dp0'; .\.venv\Scripts\Activate.ps1; uvicorn backend.app.main:app --reload"
set npm_config_cache=%~dp0frontend\.npm-cache
cd frontend
if not exist node_modules npm install
npm run dev
