# HousePrice Insight — ML Training Notes

## Dataset

- **File:** `data/processed/bengaluru_property_clean.csv`
- **Rows used:** cleaned property listings with required fields present
- **Market dataset:** not used for training (reserved for Market Insights)

## Target

- **Name:** `price`
- **Unit:** INR lakhs
- Convert to INR rupees in the UI later with `price * 100000` if needed

## Features

Final model features:

- `area_type`
- `location` (rare locations grouped to `Other` using train-only counts)
- `total_sqft`
- `bhk`
- `bath`
- `balcony` (median imputation inside pipeline)
- `is_ready_to_move` (derived from `availability`)

Excluded:

- `price_per_sqft` (target leakage)
- `society` (high missingness)
- raw high-cardinality availability date strings
- market-history features

## Preprocessing

- Fit only on training data
- Numeric: median impute + standard scale
- `area_type`: one-hot (`handle_unknown='ignore'`)
- `location`: rare-group (`min_count=10` on train) + one-hot (`handle_unknown='ignore'`)
- Packaged in a scikit-learn `Pipeline`

## Models compared

1. Linear Regression
2. Random Forest Regressor
3. HistGradientBoostingRegressor

## Evaluation methodology

- Train/test split: 80/20, `random_state=42`
- 5-fold CV on training set for model selection
- Primary selection metric: **MAE**
- Also report RMSE and R²
- Final test metrics computed once after selection

## How to retrain

From project root or any cwd:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m ml.train_model
```

Artifacts written:

- `backend/ml/house_price_model.pkl`
- `backend/ml/model_metadata.json`
- `data/ml/model_comparison.csv`
- `data/ml/model_evaluation.json`
- `data/ml/feature_summary.json`
- `data/ml/feature_importance.csv`

## Limitations

- Listing-style historical data, not verified sale deeds
- Not a professional valuation
- Sparse localities are less reliable
- Residual-based estimated ranges are not confidence intervals
