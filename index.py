"""
Optional root re-export of the FastAPI app.

Vercel is configured to load backend.main:app (see pyproject.toml).
This module remains for local smoke checks: python -c "import index; ..."
"""

from __future__ import annotations

from backend.main import app

__all__ = ["app"]
