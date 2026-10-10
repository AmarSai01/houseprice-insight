"""
Compatibility shim → backend.main:app (canonical Vercel entrypoint).
"""

from __future__ import annotations

from backend.main import app

__all__ = ["app"]
