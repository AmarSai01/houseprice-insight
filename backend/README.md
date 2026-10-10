# Backend — Bengaluru House Price API

FastAPI service that serves the Phase 4 production scikit-learn pipeline
(`backend/ml/house_price_model.pkl`).

## Quick start (development)

PostgreSQL is the only supported application database (no SQLite fallback).
The app does **not** auto-load `.env` files — set process environment variables.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://houseprice_app:YOUR_PASSWORD@127.0.0.1:5432/houseprice_dev"
uvicorn main:app --reload --port 8001
```

- API docs: http://localhost:8001/docs
- Health: http://localhost:8001/health

## Run tests

Tests require `TEST_DATABASE_URL` pointing at **exactly** `houseprice_test`.
They never fall back to `DATABASE_URL` and reject `houseprice_dev` / production DBs.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:TEST_DATABASE_URL="postgresql+psycopg://houseprice_app:YOUR_PASSWORD@127.0.0.1:5432/houseprice_test"
pytest -q
```

## Production startup

Do **not** use `--reload` in production.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:APP_ENV="production"
$env:SECRET_KEY="replace-with-a-strong-random-secret"
$env:CORS_ORIGINS="https://your-frontend.example"
$env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@PROD_HOST:5432/houseprice_prod"
# Optional: $env:PORT="8001"; $env:WEB_CONCURRENCY="1"
python -m run_production
```

Equivalent: `python run_production.py`

| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | `development` | Set `production` for fail-closed SECRET_KEY / CORS rules |
| `PORT` | `8001` | Deployment-provided listen port |
| `WEB_CONCURRENCY` | `1` | Uvicorn workers |
| `SECRET_KEY` | — | Required strong value in production |
| `CORS_ORIGINS` | — | Required in production |
| `DATABASE_URL` | — | **Required always** — PostgreSQL (`postgresql+psycopg://...`) |
| `TEST_DATABASE_URL` | — | **Required for pytest** — must be database `houseprice_test` |

Binds to `0.0.0.0`. FastAPI startup (`init_db`, model load) is unchanged.

## Vercel (serverless FastAPI)

Local uvicorn setup above is unchanged. For Vercel, use a **separate** Vercel project with:

- **Root Directory:** repository root (`.`), not `backend/`
- **Entrypoint:** repository-root `index.py` (configured in root `pyproject.toml` as `index:app`)
- **Runtime requirements:** root `requirements.txt` (pytest omitted)
- **Bundle filters:** root `.vercelignore` (excludes `frontend/`, tests, raw/EDA data)

Set the same production env vars as above (`APP_ENV`, `SECRET_KEY`, `CORS_ORIGINS`, `DATABASE_URL`). Point `CORS_ORIGINS` at the frontend Vercel URL.

Cold starts load the Random Forest pickle and CSV services into memory (Hobby max 2 GB / 60s function duration configured in root `vercel.json`). Admin retrain may exceed serverless time limits; prefer running retrain on a long-lived host.

## Prediction API

### `POST /api/predict`

Guest-capable. Authentication is **not** required.

If a valid Bearer token is provided, the estimate is also saved to the user's
prediction history.

#### Request fields

| Field | Type | Rules |
|---|---|---|
| `area_type` | string | required, non-empty |
| `location` | string | required, Bengaluru locality (unseen values are handled safely) |
| `total_sqft` | number | `> 0` |
| `bhk` | integer | `>= 1` |
| `bath` | number | `>= 1` |
| `balcony` | number | `>= 0` |
| `is_ready_to_move` | boolean | required |

`price_per_sqft` is **never** accepted as a model input.

Example:

```json
{
  "area_type": "Super built-up  Area",
  "location": "Whitefield",
  "total_sqft": 1200,
  "bhk": 2,
  "bath": 2,
  "balcony": 1,
  "is_ready_to_move": true
}
```

#### Response fields

| Field | Meaning |
|---|---|
| `estimated_price_lakhs` | Model point estimate (INR lakhs) |
| `estimated_price_inr` | Same estimate × 100,000 |
| `estimated_low_lakhs` / `estimated_high_lakhs` | Error-based estimated range (not a CI) |
| `estimated_low_inr` / `estimated_high_inr` | Range in INR |
| `price_per_sqft` | Display-only: `estimated_price_inr / total_sqft` |
| `model` / `model_version` | Selected production model identity |
| `disclaimer` | Non-valuation disclaimer |
| `range_note` | Explains residual-based range methodology |
| `prediction_id` / `saved` | Present when an authenticated save succeeds |

### `GET /api/model-info`

Returns transparency fields from `ml/model_metadata.json` (model name/version,
training date, dataset size, features, CV/test metrics, limitations).

Internal filesystem paths are not exposed.

### `GET /api/predict/history`

Requires authentication. Returns the signed-in user's saved predictions.

### `GET /health`

Returns `{ "status": "healthy", "api": "ok", "model_loaded": true|false }`.
Does not run a prediction.

## Auth endpoints (unchanged)

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

## Run tests

See **Run tests** above. The suite uses FastAPI `TestClient`, the production model
artifact, and the isolated `houseprice_test` PostgreSQL database.

## Retrain the model

Do **not** retrain during normal API operation. To rebuild artifacts after data
or pipeline changes:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m ml.train_model
```

This writes:

- `ml/house_price_model.pkl`
- `ml/model_metadata.json`
- supporting reports under `../data/ml/`

Restart the API process after retraining so the new artifact is loaded.

## Database configuration

- PostgreSQL only (`postgresql+psycopg://...`). SQLite URLs are rejected.
- `DATABASE_URL` is **required** in every environment (no silent default).
- Local development database name: `houseprice_dev`.
- Automated tests database name: `houseprice_test` via `TEST_DATABASE_URL`.
- An existing `backend/house_prediction.db` SQLite file (if present) is a legacy backup
  and is not used by the application.

## Important notes

- Target unit is **INR lakhs**.
- Market-history data is not used by this prediction endpoint.
- Predictions are ML estimates, not professional property valuations.
