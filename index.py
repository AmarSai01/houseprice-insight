"""
Vercel FastAPI entrypoint for HousePrice Insight (repository root).

Vercel resolves tool.vercel.entrypoint = "index:app" to this file.
Local development is unchanged: run uvicorn from the backend/ directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_BACKEND_DIR = _REPO_ROOT / "backend"

if not _BACKEND_DIR.is_dir():
    raise ImportError(
        "HousePrice Insight backend/ directory is missing from the deployment bundle. "
        "Deploy the API Vercel project with Root Directory = repository root (.)."
    )

# Flat backend imports (cors_settings, routes, ml, ...) require backend/ on sys.path.
# Repo root must remain importable so data/ paths resolve via backend/ml parents[1].
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from main import app  # noqa: E402
except RuntimeError:
    # Fail closed with the original message (DATABASE_URL / SECRET_KEY / CORS_ORIGINS).
    raise
except ModuleNotFoundError as exc:
    # Only rewrite the flat-layout miss; keep dependency ImportErrors visible.
    if getattr(exc, "name", None) == "main":
        raise ImportError(
            "Failed to import backend/main.py. "
            "Deploy the API project with Root Directory = repository root (.) "
            "so backend/ is present in the bundle."
        ) from exc
    raise

__all__ = ["app"]
