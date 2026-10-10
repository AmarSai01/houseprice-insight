"""
Production ASGI entrypoint for HousePrice Insight.

Usage (from the backend directory):

    set APP_ENV=production
    set SECRET_KEY=...
    set CORS_ORIGINS=...
    set DATABASE_URL=...
    python -m run_production

Or:

    python run_production.py

Never enables --reload. Binds to 0.0.0.0. PORT defaults to 8001.
WEB_CONCURRENCY defaults to 1.

FastAPI startup events (init_db, model load) remain on the app; this module
only configures how uvicorn serves main:app.
"""

from __future__ import annotations

import uvicorn

from startup_settings import build_production_uvicorn_kwargs


def main() -> None:
    kwargs = build_production_uvicorn_kwargs()
    uvicorn.run(**kwargs)


if __name__ == "__main__":
    main()
