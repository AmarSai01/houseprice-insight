"""Ensure Vercel-facing dependency manifests declare FastAPI and stay aligned."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _requirement_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        # Strip extras/version markers: fastapi==x / uvicorn[standard]==x
        name = re.split(r"[<=>!~\[]", raw, maxsplit=1)[0].strip().lower()
        if name:
            names.add(name)
    return names


def test_pyproject_declares_fastapi_for_vercel_uv_install():
    """
    Vercel uses `uv sync` against pyproject.toml when that file exists.
    A [project] table without dependencies installs nothing — FastAPI missing.
    """
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies") or []
    assert deps, "pyproject.toml [project.dependencies] must not be empty for Vercel"
    joined = "\n".join(str(item) for item in deps).lower()
    assert "fastapi" in joined
    assert data.get("tool", {}).get("vercel", {}).get("entrypoint") == "backend.main:app"


def test_root_requirements_mirror_pyproject_runtime_deps():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_names = _requirement_names(
        "\n".join(str(item) for item in data["project"]["dependencies"])
    )
    requirements_names = _requirement_names(
        (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    )
    assert pyproject_names == requirements_names
    assert "fastapi" in pyproject_names
    assert "pytest" not in pyproject_names
