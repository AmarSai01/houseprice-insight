#!/bin/bash
# =============================================================================
# LEGACY DEVELOPMENT HELPER — DO NOT USE FOR PRODUCTION
# =============================================================================
# Production command (from the backend directory):
#   python -m run_production
#
# This script is for local development only. It enables --reload and must never
# be used as a production process entrypoint.
# =============================================================================

set -euo pipefail

echo "WARNING: start.sh is a legacy development helper."
echo "Do NOT use this script in production. Use: python -m run_production"
echo ""

# Prefer the documented Python 3.13 venv, then fall back to older names.
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# Production artifact check only — do not auto-train from this helper.
if [ ! -f "ml/house_price_model.pkl" ]; then
  echo "ERROR: ml/house_price_model.pkl is missing."
  echo "Train separately if needed: python -m ml.train_model"
  echo "Then restart. This script will not retrain automatically."
  exit 1
fi

echo "Starting FastAPI (development --reload) on port 8001..."
uvicorn main:app --reload --port 8001
