"""
Vercel Python / FastAPI entrypoint for HousePrice Insight.

Keeps the existing backend import layout (flat modules under backend/) by
putting that directory on sys.path, then re-exports the FastAPI `app`.

Local development is unchanged: run uvicorn from the backend/ directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _REPO_ROOT / "backend"

# Ensure repo-root `data/` resolves the same as local monorepo layout
# (model_service / market / similar_properties use backend/ml → parents[1]).
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from main import app  # noqa: E402

__all__ = ["app"]
