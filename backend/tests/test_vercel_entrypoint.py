"""Vercel entrypoint and import-time DB initialization regressions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
PYTHON = sys.executable


def _database_url_for_tests() -> str:
    env_value = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env_value and str(env_value).strip():
        return str(env_value).strip()
    local = BACKEND_DIR / ".local" / "test_database_url"
    if local.is_file():
        text = local.read_text(encoding="utf-8").strip()
        if text:
            return text
    pytest.skip("TEST_DATABASE_URL / DATABASE_URL / .local/test_database_url required")


def _run_isolated(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    # Drop DB/CORS keys then apply test env (values never printed by callers).
    for key in (
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "SECRET_KEY",
        "CORS_ORIGINS",
        "APP_ENV",
        "ENVIRONMENT",
    ):
        merged.pop(key, None)
    merged.update(env)
    merged["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [PYTHON, "-c", script],
        cwd=str(REPO_ROOT),
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_missing_database_url_raises_exact_error_on_ensure_engine():
    """Exact initialization failure that previously aborted `from main import app`."""
    script = dedent(
        """
        import sys
        from pathlib import Path
        backend = Path(r'''%s''')
        sys.path.insert(0, str(backend))
        from database_settings import MISSING_DATABASE_URL_ERROR
        from database import ensure_engine, engine
        assert engine is None
        try:
            ensure_engine()
        except RuntimeError as exc:
            assert str(exc) == MISSING_DATABASE_URL_ERROR, repr(str(exc))
            print("EXACT_OK")
        else:
            raise SystemExit("expected RuntimeError")
        """
        % BACKEND_DIR
    )
    result = _run_isolated(script, {"APP_ENV": "development"})
    assert result.returncode == 0, result.stderr
    assert "EXACT_OK" in result.stdout


def test_backend_main_imports_with_repo_root_only():
    """Vercel loads backend.main:app with project root on sys.path."""
    script = dedent(
        """
        import backend.main as module
        paths = {getattr(route, "path", None) for route in module.app.routes}
        assert module.app.title == "House Price Prediction API"
        assert "/health" in paths
        assert any(path and str(path).startswith("/api") for path in paths)
        print("IMPORT_OK")
        """
    )
    result = _run_isolated(
        script,
        {
            "APP_ENV": "development",
            "DATABASE_URL": _database_url_for_tests(),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "IMPORT_OK" in result.stdout


def test_index_and_api_shim_reexport_backend_main():
    script = dedent(
        """
        import index
        import api.index as api_index
        import backend.main as backend_main
        assert index.app is backend_main.app
        assert api_index.app is backend_main.app
        print("SHIM_OK")
        """
    )
    result = _run_isolated(
        script,
        {
            "APP_ENV": "development",
            "DATABASE_URL": _database_url_for_tests(),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "SHIM_OK" in result.stdout


def test_asgi_module_imports_without_database_url_when_engine_is_lazy():
    """
    Vercel must import the ASGI app without DATABASE_URL at import time.
    ensure_engine still fail-closes with the identical RuntimeError.
    """
    script = dedent(
        """
        import backend.main as module
        assert module.app.title == "House Price Prediction API"
        from database_settings import MISSING_DATABASE_URL_ERROR
        from database import ensure_engine
        try:
            ensure_engine()
        except RuntimeError as exc:
            assert str(exc) == MISSING_DATABASE_URL_ERROR
            print("LAZY_OK")
        else:
            raise SystemExit("expected RuntimeError from ensure_engine")
        """
    )
    result = _run_isolated(script, {"APP_ENV": "development"})
    assert result.returncode == 0, result.stderr
    assert "LAZY_OK" in result.stdout


def test_legacy_from_main_import_app_path_still_works_locally():
    """Local uvicorn layout: backend/ on sys.path, `from main import app`."""
    script = dedent(
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(r'''%s''')))
        from main import app
        assert app.title == "House Price Prediction API"
        print("LOCAL_OK")
        """
        % BACKEND_DIR
    )
    result = _run_isolated(
        script,
        {
            "APP_ENV": "development",
            "DATABASE_URL": _database_url_for_tests(),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "LOCAL_OK" in result.stdout


def test_main_loads_when_package_init_path_setup_is_skipped():
    """
    Reproduce Vercel: load backend/main.py as backend.main without running
    backend/__init__.py path bootstrap. Flat imports must still resolve
    (cors_settings, database, routes, ml).
    """
    script = dedent(
        """
        import importlib.util
        import sys
        import types
        from pathlib import Path

        root = Path(r'''%s''')
        backend = root / "backend"
        # Repo root only — do not pre-add backend/ (Vercel-like).
        sys.path = [p for p in sys.path if Path(p).resolve() != backend.resolve()]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        # Stub parent package without executing backend/__init__.py
        pkg = types.ModuleType("backend")
        pkg.__path__ = [str(backend)]
        sys.modules["backend"] = pkg

        spec = importlib.util.spec_from_file_location(
            "backend.main", backend / "main.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["backend.main"] = mod
        spec.loader.exec_module(mod)
        assert mod.app.title == "House Price Prediction API"
        from cors_settings import CORS_ORIGINS  # noqa: F401
        print("SPEC_LOAD_OK")
        """
        % REPO_ROOT
    )
    result = _run_isolated(
        script,
        {
            "APP_ENV": "development",
            "DATABASE_URL": _database_url_for_tests(),
        },
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "SPEC_LOAD_OK" in result.stdout
