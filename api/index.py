"""
Compatibility shim.

The Vercel FastAPI entrypoint is the repository-root index.py
(tool.vercel.entrypoint = "index:app"). Keeping this module avoids breaking
any tooling that still imports api.index while steering clear of treating
/api as a file-based Python function entry.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load root index.py as the canonical entry (not the stdlib, not this package).
_spec = importlib.util.spec_from_file_location(
    "houseprice_vercel_index",
    _REPO_ROOT / "index.py",
)
if _spec is None or _spec.loader is None:
    raise ImportError("Unable to load repository-root index.py for Vercel.")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app

__all__ = ["app"]
