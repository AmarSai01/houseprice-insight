# HousePrice Insight

A full-stack house price estimation app built with FastAPI, React (Vite + Tailwind), and scikit-learn.

**Product direction:** Instant Estimate + Why  
**Current stage:** Phase 5 — production Bengaluru ML model is served by FastAPI.  
`POST /api/predict` is guest-capable (authentication is optional for saving history). See the live application for the current frontend experience.

This is a model-based estimator for learning and portfolio use. It is **not** a guaranteed market appraisal or professional valuation service.

## Features (current)

- JWT authentication (register / login)
- Guest-capable prediction API with INR lakhs estimate + error-based range
- Prediction history for signed-in users
- Production RandomForestRegressor pipeline (`house_price_model.pkl`)
- Model transparency via `GET /api/model-info`
- OpenAPI docs at `/docs` in development only (disabled in production)

## Tech stack

- **Frontend:** React, Vite, Tailwind CSS, Axios, React Router
- **Backend:** FastAPI, Uvicorn, SQLAlchemy, PostgreSQL
- **ML:** pandas, NumPy, scikit-learn
- **Auth:** JWT (python-jose) + bcrypt

## Project structure

```
project/
├── index.py                    # Optional re-export of backend.main:app
├── api/index.py                # Compatibility shim → backend.main:app
├── vercel.json                 # API project function settings
├── .vercelignore               # Keep API bundle lean (excludes frontend/)
├── requirements.txt            # Vercel API runtime deps (no pytest)
├── pyproject.toml              # tool.vercel.entrypoint = backend.main:app
├── backend/
│   ├── __init__.py             # Puts backend/ on sys.path for flat imports
│   ├── main.py                 # FastAPI app (local uvicorn + Vercel entry)
│   ├── run_production.py       # Long-lived uvicorn production entry
│   ├── requirements.txt        # Local/dev deps (includes pytest)
│   ├── routes/
│   └── ml/
│       ├── house_price_model.pkl
│       └── model_metadata.json
├── frontend/
│   ├── vercel.json             # SPA rewrites (separate Vercel project)
│   ├── src/
│   └── package.json
└── data/
    ├── processed/              # Runtime datasets (required on API deploy)
    ├── ml/                     # Explanation + evaluation artifacts
    ├── eda/
    └── raw/
```

See `backend/README.md` for prediction request/response details and tests.

## Prerequisites

- Python **3.13** (project is set up for 3.13)
- Node.js 16+ and npm

## Setup

### 1. Backend

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
# Model artifacts should already exist from Phase 4.
# To retrain: python -m ml.train_model
# PostgreSQL only — the app does not auto-load .env files.
$env:DATABASE_URL="postgresql+psycopg://houseprice_app:YOUR_PASSWORD@127.0.0.1:5432/houseprice_dev"
uvicorn main:app --reload --port 8001
```

- API: http://localhost:8001
- Docs: http://localhost:8001/docs
- Health: http://localhost:8001/health

**Backend tests** (isolated `houseprice_test` database only):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:TEST_DATABASE_URL="postgresql+psycopg://houseprice_app:YOUR_PASSWORD@127.0.0.1:5432/houseprice_test"
pytest -q
```

**Production startup** (no `--reload`; binds `0.0.0.0`):

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

Optional admin user (API only; there is no admin UI):

The script accepts an email and password as command-line arguments. Run it only in a trusted environment and use a unique, strong password; avoid shared or example credentials. Command-line arguments may be retained in shell history or visible to local processes.

### 2. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

- App: http://localhost:3000

**Production frontend build**

```powershell
cd frontend
npm run build
```

Output: `frontend/dist/` (includes `dist/index.html` and hashed assets).

**Static hosting / SPA rewrite**

The frontend uses React Router `BrowserRouter`. Static hosts must rewrite unknown/non-file requests to `/index.html` so deep links and refreshes work.

Example: a direct visit to `https://production-domain.example/market` must serve `index.html`; React Router then renders `/market`.

`frontend/vercel.json` already configures the SPA rewrite. See `frontend/README.md`.

## Deploy on Vercel (two projects, one repo)

Use **two** Vercel projects against the same GitHub repository. Do not put FastAPI and the React SPA in one project (the SPA rewrite would fight API routes).

### A) Frontend project

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite |
| Env | `VITE_API_URL` = public API origin; `APP_ENV=production` recommended |

Uses existing `frontend/vercel.json`.

### B) Backend (API) project

| Setting | Value |
|---|---|
| Root Directory | `.` (repository root) |
| Entry | `backend/main.py` → `backend.main:app` (see `pyproject.toml`) |
| Dependencies | `pyproject.toml` `[project.dependencies]` (Vercel/`uv` install source) |

**Required env vars (Production):** `APP_ENV=production`, `SECRET_KEY`, `CORS_ORIGINS` (your Vercel frontend origin), `DATABASE_URL` (`postgresql+psycopg://...` to hosted Postgres). Optional: `FRONTEND_BASE_URL`, SMTP settings.

**Included at runtime:** `backend/ml/house_price_model.pkl`, processed CSVs, and `data/ml` explanation/evaluation artifacts (see `.vercelignore`).

**Not on Vercel:** PostgreSQL itself — use Neon, Supabase, RDS, etc. Local `python -m run_production` remains the long-lived alternative.

**Hobby note:** Python bundles are capped at ~500 MB uncompressed. This app’s ML stack + ~40 MB model is expected to fit but is tight; if the deploy fails on size, enable Large Functions (Fluid) or host the API on Railway/Render/Fly instead.

## Usage

1. Register or log in
2. Open the dashboard
3. Enter property details:
   - Location
   - Square feet
   - Bedrooms
   - Bathrooms
   - Furnishing
   - Area type
4. Submit to get an estimated price
5. Review your prediction history

## API endpoints

### Authentication
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### Predictions
- `POST /api/predict` (guest-capable; auth optional to save history)
- `GET /api/predict/history` (auth required)
- `GET /api/model-info`

### Admin API (admin role, no UI)
- `GET /api/admin/users`
- `GET /api/admin/predictions`
- `GET /api/admin/metrics`
- `POST /api/admin/retrain`
- `DELETE /api/admin/users/{user_id}`
- `PATCH /api/admin/users/{user_id}/role`

## Retraining the model

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m ml.train_model
```

Artifacts are written to `backend/ml/house_price_model.pkl` and `backend/ml/model_metadata.json`.

## Environment variables

Process environment variables (the app does not load a `.env` file automatically; see `backend/.env.example` and `frontend/.env.example`):

```env
APP_ENV=development
SECRET_KEY=replace-with-a-strong-random-secret
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001
DATABASE_URL=postgresql+psycopg://houseprice_app:YOUR_PASSWORD@127.0.0.1:5432/houseprice_dev
TEST_DATABASE_URL=postgresql+psycopg://houseprice_app:YOUR_PASSWORD@127.0.0.1:5432/houseprice_test
PORT=8001
WEB_CONCURRENCY=1
VITE_API_URL=http://127.0.0.1:8001
```

| Variable | Role |
|---|---|
| `APP_ENV` | `development` (default) or `production` — gates SECRET_KEY / CORS rules |
| `SECRET_KEY` | JWT signing secret (required strong value in production) |
| `CORS_ORIGINS` | Allowed frontend origins (required in production) |
| `DATABASE_URL` | PostgreSQL URL (**required always**; `postgresql+psycopg://...`) |
| `TEST_DATABASE_URL` | PostgreSQL URL for pytest (**required for tests**; DB name must be `houseprice_test`) |
| `PORT` | Listen port for `python -m run_production` (default `8001`) |
| `WEB_CONCURRENCY` | Uvicorn worker count for production (default `1`) |
| `VITE_API_URL` | Frontend build-time API base URL |

**Database notes**

- PostgreSQL only. SQLite application URLs are rejected (legacy `backend/house_prediction.db` is unused backup).
- Local app DB: `houseprice_dev`. Test DB: `houseprice_test`. Production: host-provided (e.g. `houseprice_prod`).
- The application does not automatically load `.env` files.

**Startup notes**

- Development: `uvicorn main:app --reload --port 8001`
- Production: `python -m run_production` (never uses `--reload`; host `0.0.0.0`)

Also set a strong `SECRET_KEY` and real `CORS_ORIGINS` / `VITE_API_URL` for any production deployment.

## Model features (production)

- `area_type`, `location`, `total_sqft`, `bhk`, `bath`, `balcony`, `is_ready_to_move`
- Target: `price` (INR lakhs)
- `price_per_sqft` is display-only and never used as a model input

## Common issues

### Model not found
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m ml.train_model
```

### Backend will not start / Unicode console errors
Use ASCII-only console messages and run with `backend\.venv`.

### CORS / connection errors
- Backend on port 8001
- Frontend on port 3000
- Confirm `VITE_API_URL` / `frontend/src/services/apiBaseUrl.js` points at `http://127.0.0.1:8001`

### Database errors
Confirm `DATABASE_URL` points at a reachable PostgreSQL database (`houseprice_dev` locally).
Tables are created on startup via `create_all` for empty databases.

## Notes

- Prefer `backend/.venv` (Python 3.13). An older `backend/venv` may exist from a previous machine and should not be used.
- Admin accounts can call admin API routes; the frontend always sends users to `/dashboard`.
- Keep the frontend and backend prediction fields aligned when changing the API schema.

## License and data provenance

- `data/raw/bengaluru_house_data_raw.csv` is the 13,320-row Bengaluru housing dataset published by Amitabha Chakraborty on [Kaggle](https://www.kaggle.com/datasets/amitabhajoy/bengaluru-house-price-data). Kaggle lists it as **CC0: Public Domain**. The processed property data and trained prediction model are derived from this dataset.
- `data/raw/bengaluru_market_history_raw.csv` and `data/house_data.csv` are synthetic illustrative data created for this project; they are not verified historical market records or actual property listings. Do not present the market-history series as observed market facts.
- No software license is currently included. The CC0 data designation does not license this project's code. Choose and add a separate code license if you want others to reuse the software.
