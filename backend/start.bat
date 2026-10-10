@echo off
REM =============================================================================
REM LEGACY DEVELOPMENT HELPER — DO NOT USE FOR PRODUCTION
REM =============================================================================
REM Production command (from the backend directory):
REM   python -m run_production
REM
REM This script is for local development only. It enables --reload and must never
REM be used as a production process entrypoint.
REM =============================================================================

echo WARNING: start.bat is a legacy development helper.
echo Do NOT use this script in production. Use: python -m run_production
echo.

REM Prefer the documented Python 3.13 venv, then fall back to older names.
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
  call venv\Scripts\activate.bat
)

REM Production artifact check only — do not auto-train from this helper.
if not exist ml\house_price_model.pkl (
  echo ERROR: ml\house_price_model.pkl is missing.
  echo Train separately if needed: python -m ml.train_model
  echo Then restart. This script will not retrain automatically.
  exit /b 1
)

echo Starting FastAPI (development --reload) on port 8001...
uvicorn main:app --reload --port 8001
