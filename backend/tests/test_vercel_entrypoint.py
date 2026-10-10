"""Vercel root index.py entrypoint must export the same FastAPI app."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path


def test_vercel_root_index_exports_fastapi_app():
    repo_root = Path(__file__).resolve().parents[2]
    index_path = repo_root / "index.py"
    assert index_path.is_file()

    # Load as Vercel does: module "index" from repository root (not backend/).
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    for name in list(sys.modules):
        if name in {"index", "api", "api.index"} or name.startswith("api."):
            del sys.modules[name]

    spec = importlib.util.spec_from_file_location("index", index_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["index"] = module
    spec.loader.exec_module(module)

    assert hasattr(module, "app")
    assert module.app.title == "House Price Prediction API"

    from main import app as backend_app

    assert module.app is backend_app


def test_vercel_api_shim_still_exports_app():
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    for name in list(sys.modules):
        if name == "api" or name.startswith("api.") or name == "houseprice_vercel_index":
            del sys.modules[name]

    module = importlib.import_module("api.index")
    assert module.app.title == "House Price Prediction API"
