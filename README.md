<div align="center">

<a href="https://housepriceinsight.amarsai.in"><img src="docs/readme/banner.png" alt="HousePrice Insight: Bengaluru property price estimation" width="100%"></a>

<br>

[![Live site](https://img.shields.io/badge/live-housepriceinsight.amarsai.in-1f2c26?style=for-the-badge&labelColor=a8834b)](https://housepriceinsight.amarsai.in)
[![Test R²](https://img.shields.io/badge/test_R²-0.69-1f2c26?style=for-the-badge&labelColor=a8834b)](#-model-results)
[![License: MIT](https://img.shields.io/badge/license-MIT-1f2c26?style=for-the-badge&labelColor=a8834b)](LICENSE)

![Python](https://img.shields.io/badge/Python-3.13-1f2c26?logo=python&logoColor=f1eee6)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1f2c26?logo=scikitlearn&logoColor=f1eee6)
![pandas](https://img.shields.io/badge/pandas-1f2c26?logo=pandas&logoColor=f1eee6)
![FastAPI](https://img.shields.io/badge/FastAPI-1f2c26?logo=fastapi&logoColor=f1eee6)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-1f2c26?logo=postgresql&logoColor=f1eee6)
![React](https://img.shields.io/badge/React_18-1f2c26?logo=react&logoColor=f1eee6)
![Vite](https://img.shields.io/badge/Vite-1f2c26?logo=vite&logoColor=f1eee6)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-1f2c26?logo=tailwindcss&logoColor=f1eee6)
![Vercel](https://img.shields.io/badge/Vercel-1f2c26?logo=vercel&logoColor=f1eee6)

**Know what a Bengaluru property is worth, and why.**<br>
An instant price estimate with an honest range, the features that drive the model, and similar recorded properties to check it against.

[**Try it live →**](https://housepriceinsight.amarsai.in) &nbsp;·&nbsp; [Results](#-model-results) &nbsp;·&nbsp; [How it works](#-ml-pipeline) &nbsp;·&nbsp; [Run locally](#-run-locally)

</div>

---

## 💡 Why

Property prices in Bengaluru swing widely between localities, and most "price calculators" give one number with no context. HousePrice Insight gives **an estimate, a realistic range, and the evidence behind it**: which features the model relies on, and which real listings are most similar.

It is built to be honest about its limits. The range comes from the model's real past errors, not a made-up confidence band. Price per sq.ft. is shown but never used as a model input, so there is no target leakage. The app says plainly that it is decision support, not a professional valuation.

## ✨ Features

| | |
|---|---|
| 🏷️ **Instant estimate** | Pick a locality (208 the model knows), area type, size, BHK, bathrooms, balconies and ready-to-move status. You get the price in ₹ lakhs and the ₹/sq.ft. |
| ↔️ **Estimated range** | Lower and upper bounds from the 10th and 90th percentile of the model's out-of-fold errors. |
| 🧭 **What the model relies on** | Model-wide feature influence (permutation importance). It is clearly labelled as *not* a per-property rupee breakdown. |
| 🏘️ **Similar properties** | Nearest recorded listings from the cleaned dataset, found by a weighted feature distance in which price is never used. |
| ⚖️ **Compare** and 💰 **Affordability** | Put two property profiles side by side, then check the EMI and budget fit for an estimate. |
| 📈 **Market view** | Historical ₹/sq.ft. trends for four localities. This is an illustrative series, labelled as such in the app. |
| 🔐 **Accounts** | Optional sign-up with JWT and bcrypt to save estimate history, plus a password reset by email. Guests can estimate without an account. |

## 📸 Screenshots

<table>
<tr>
<td width="50%"><img src="docs/readme/screenshots/home.jpg" alt="HousePrice Insight landing page"><br><sub><b>Home</b>: Bengaluru property intelligence</sub></td>
<td width="50%"><img src="docs/readme/screenshots/estimate.jpg" alt="Valuation report for a 3 BHK in Whitefield with estimated range"><br><sub><b>Estimate</b>: a live valuation report with its range</sub></td>
</tr>
<tr>
<td colspan="2"><img src="docs/readme/screenshots/market.jpg" alt="Market page showing ₹ per sq.ft. for four localities"><br><sub><b>Market</b>: ₹/sq.ft. by locality (illustrative data)</sub></td>
</tr>
</table>

## 🏗️ Architecture

```mermaid
flowchart LR
    U([User's browser]) --> FE["React 18 + Vite SPA<br/><sub>Vercel project: frontend/</sub>"]
    FE -- "Axios · VITE_API_URL" --> API["FastAPI<br/><sub>Vercel project: repo root</sub>"]
    API --> M[("house_price_model.pkl<br/>RandomForest pipeline")]
    API --> CSV[("Clean Bengaluru listings<br/>similar-property search")]
    API --> ART[("data/ml artifacts<br/>feature influence · evaluation")]
    API --> DB[("PostgreSQL<br/>users · estimate history")]
    API -. "password reset" .-> SMTP[["SMTP email"]]

    classDef ui fill:#f1eee6,stroke:#1f2c26,color:#161513
    classDef svc fill:#1f2c26,stroke:#1f2c26,color:#f1eee6
    classDef store fill:#f1eee6,stroke:#a8834b,color:#161513
    class U,FE ui
    class API svc
    class M,CSV,ART,DB,SMTP store
```

The frontend and the API are two Vercel projects deployed from the same repository. The trained model and data artifacts ship with the API bundle. PostgreSQL is hosted separately.

## 🧠 ML pipeline

```mermaid
flowchart LR
    A["Kaggle Bengaluru<br/>house data<br/><sub>13,320 rows</sub>"] --> B["Clean + audit<br/><sub>12,679 usable rows</sub>"]
    B --> C["Features<br/><sub>area type, location,<br/>sq.ft., BHK, bath,<br/>balcony, ready-to-move</sub>"]
    C --> D["Preprocess<br/><sub>rare localities → Other<br/>one-hot + scaling</sub>"]
    D --> E["5-fold CV<br/><sub>Linear · RandomForest ·<br/>HistGradientBoosting</sub>"]
    E --> F["Pick lowest CV MAE<br/><b>RandomForest</b><br/><sub>200 trees</sub>"]
    F --> G["Held-out test<br/><sub>20% · 2,536 rows</sub>"]
    G --> H["FastAPI<br/>POST /api/predict"]
    H --> I["React UI"]

    classDef data fill:#f1eee6,stroke:#6b665d,color:#161513
    classDef model fill:#1f2c26,stroke:#1f2c26,color:#f1eee6
    classDef serve fill:#f1eee6,stroke:#a8834b,color:#161513
    class A,B,C,D data
    class E,F,G model
    class H,I serve
```

- **Target:** price in ₹ lakhs. **Split:** 80/20 (10,143 train, 2,536 test), seed 42.
- **Leakage guard:** `price_per_sqft`, the society name and the market-history series are all excluded from training.
- **Rare localities** (fewer than 10 listings) are grouped as *Other* during training, so estimates for sparse areas are less reliable, and the app says so.
- **Range:** the 10th and 90th percentiles of out-of-fold residuals (−₹37.8 L / +₹39.4 L), applied around each prediction.

## 📊 Model results

Model selection used 5-fold cross-validation on the training set, and the winner was then scored once on the held-out 20%.

| Model | CV MAE (₹ L) | CV RMSE (₹ L) | CV R² |
|---|---:|---:|---:|
| **RandomForestRegressor** ✅ | **33.07 ± 1.33** | **81.72** | **0.68** |
| HistGradientBoostingRegressor | 33.71 ± 1.12 | 82.73 | 0.68 |
| LinearRegression | 41.02 ± 1.42 | 87.76 | 0.63 |

**Held-out test set (RandomForest):** R² **0.69** · MAE **₹30.8 L** · RMSE ₹71.1 L

**What drives the model** (native tree importance): property size dominates at about 74%, followed by bathrooms (8%) and BHK (3%), with locality and area type making up most of the rest.

> Bengaluru prices have a long tail of luxury listings, which is why RMSE sits well above MAE. Treat the range, not the single number, as the answer.

## 🧰 Tech stack

| Layer | Tools |
|---|---|
| **ML / data** | scikit-learn, pandas, NumPy, joblib |
| **API** | FastAPI, Uvicorn, SQLAlchemy 2, psycopg 3, Pydantic 2, PyJWT, bcrypt |
| **Database** | PostgreSQL |
| **Frontend** | React 18, Vite, Tailwind CSS 4, React Router 7, Axios, Lucide |
| **Testing** | Pytest (isolated `houseprice_test` database), Node test runner |
| **Hosting** | Vercel (two projects: SPA and API) |

## 🗂️ Project structure

```text
├── backend/
│   ├── main.py              FastAPI app (local uvicorn + Vercel entry)
│   ├── routes/              auth, predict, properties, market, model_evaluation, admin
│   ├── ml/                  train_model.py, model_service.py, explanation.py,
│   │                        similar_properties.py, house_price_model.pkl, model_metadata.json
│   └── tests/               API, settings, prediction and Vercel entrypoint tests
├── data/
│   ├── raw/                 Kaggle source CSV (+ synthetic market history)
│   ├── processed/           cleaned listings used for training and similarity
│   ├── ml/                  CV comparison, feature importance, predicted-vs-actual
│   ├── eda/                 EDA scripts, SVG figures and reports
│   └── reports/             dataset audit + cleaning reports
├── frontend/src/            pages, components, services (API, EMI, compare)
└── pyproject.toml           API dependencies for the Vercel build
```

## 🚀 Run locally

You need Python 3.13, Node.js 18+ and a local PostgreSQL database (`houseprice_dev`).

```bash
git clone https://github.com/AmarSai01/houseprice-insight.git
cd houseprice-insight/backend

python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# The app reads real environment variables (it does not load .env files automatically)
set DATABASE_URL=postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/houseprice_dev
uvicorn main:app --reload --port 8001     # docs at http://localhost:8001/docs
```

```bash
# Frontend (second terminal)
cd frontend
npm install
npm run dev                               # http://localhost:3000
```

<details>
<summary><b>Retrain, test and deploy</b></summary>

```bash
cd backend
python -m ml.train_model     # rewrites house_price_model.pkl + model_metadata.json
pytest -q                    # needs TEST_DATABASE_URL pointing at houseprice_test
cd ../frontend && npm test
```

Environment variables, the two-project Vercel setup and the admin API are documented in [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) and [`backend/README.md`](backend/README.md).

</details>

## 📚 Data and licence

- **Listings:** the [Bengaluru House Price Data](https://www.kaggle.com/datasets/amitabhajoy/bengaluru-house-price-data) by Amitabha Chakraborty on Kaggle (CC0: Public Domain). The processed data and the trained model are derived from it.
- **Market history** (`bengaluru_market_history_raw.csv`) is **synthetic, illustrative data** made for this project. It is not observed market records.
- The code is released under the [MIT License](LICENSE). The dataset terms are separate.

> This is an ML-based estimate for learning and portfolio use, not a professional property valuation.

## 👋 Contact

**Amar Sai** (Amareshwar Thuraka)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-amareshwar9347-1f2c26?style=flat-square&logo=linkedin&logoColor=f1eee6)](https://www.linkedin.com/in/amareshwar9347)
[![GitHub](https://img.shields.io/badge/GitHub-AmarSai01-1f2c26?style=flat-square&logo=github&logoColor=f1eee6)](https://github.com/AmarSai01)

If this project helped you, a ⭐ is appreciated.
