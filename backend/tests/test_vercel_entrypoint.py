"""Vercel api.index entrypoint must export the same FastAPI app."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_vercel_api_index_exports_fastapi_app():
    repo_root = Path(__file__).resolve().parents[2]
    api_dir = repo_root / "api"
    assert (api_dir / "index.py").is_file()

    # Fresh import path similar to Vercel's repository-root layout.
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Drop cached modules so this test does not depend on import order.
    for name in list(sys.modules):
        if name == "api" or name.startswith("api."):
            del sys.modules[name]

    module = importlib.import_module("api.index")
    assert hasattr(module, "app")
    assert module.app.title == "House Price Prediction API"

    from main import app as backend_app

    assert module.app is backend_app
