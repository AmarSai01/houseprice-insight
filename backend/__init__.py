"""
Backend package marker for Vercel (`backend.main:app`).

Flat imports inside this package (`from cors_settings import ...`, `from ml...`)
expect the backend directory itself on sys.path — the same layout used when
running `uvicorn main:app` from backend/ locally.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
