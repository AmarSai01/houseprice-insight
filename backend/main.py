"""
Main FastAPI application.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Vercel loads backend.main via a file/module spec that may not execute
# backend/__init__.py first. Flat imports (cors_settings, database, routes, ml)
# require this directory on sys.path — same layout as local `uvicorn main:app`.
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from cors_settings import ALLOW_CREDENTIALS, CORS_ORIGINS
from database import init_db, ping_database
from ml.model_service import get_model_service
from openapi_settings import resolve_openapi_docs_kwargs
from routes import auth, predict, admin, market, properties, model_evaluation

logger = logging.getLogger(__name__)

app = FastAPI(
    title="House Price Prediction API",
    description="API for predicting Bengaluru house prices using machine learning",
    version="1.1.0",
    **resolve_openapi_docs_kwargs(),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(market.router)
app.include_router(properties.router)
app.include_router(model_evaluation.router)
app.include_router(admin.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """Return clean validation errors without internal traceback details."""
    errors = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", []) if part != "body"]
        field = ".".join(loc) if loc else "request"
        errors.append({"field": field, "message": err.get("msg", "Invalid value")})
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request.", "errors": errors},
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database and warm the model / similarity services."""
    init_db()
    service = get_model_service()
    from ml.similar_properties import get_similar_properties_service

    similar = get_similar_properties_service()
    if service.loaded:
        print("Database initialized; production model loaded")
    else:
        print("Database initialized; WARNING: production model not loaded")
    if similar.loaded:
        print("Similar-properties dataset loaded")
    else:
        print("WARNING: similar-properties dataset not loaded")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "House Price Prediction API",
        "docs": "/docs",
        "version": "1.1.0",
    }


@app.get("/health")
async def health_check():
    """
    Readiness-oriented health check.

    - Does not run predictions or reload the model.
    - Requires the in-memory production model flag and a lightweight DB ping.
    - Returns HTTP 503 when not ready; never includes filesystem paths or secrets.
    """
    service = get_model_service()
    model_loaded = bool(service.loaded)
    database_ok = ping_database()
    if not database_ok:
        logger.error("Health check: database connectivity failed (SELECT 1).")

    ready = model_loaded and database_ok
    body = {
        "status": "healthy" if ready else "unhealthy",
        "api": "ok",
        "model_loaded": model_loaded,
        "database": "ok" if database_ok else "unavailable",
    }
    if ready:
        return body
    return JSONResponse(status_code=503, content=body)


@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests to prevent 404 errors."""
    return {"detail": "No favicon"}
