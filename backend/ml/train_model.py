"""
Train and evaluate the Bengaluru house-price model.

Uses cleaned property data only.
Saves production artifacts under backend/ml/ and evaluation artifacts under data/ml/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.explanation import build_global_feature_influence
from ml.transformers import FeatureBuilder, RareLocationGrouper

ML_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ML_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_CSV = DATA_DIR / "processed" / "bengaluru_property_clean.csv"
DATA_ML_DIR = DATA_DIR / "ml"

MODEL_PATH = ML_DIR / "house_price_model.pkl"
METADATA_PATH = ML_DIR / "model_metadata.json"

RANDOM_STATE = 42
RARE_LOCATION_MIN_COUNT = 10
MODEL_VERSION = "1.0.0"

def load_dataset() -> pd.DataFrame:
    if not PROCESSED_CSV.exists():
        raise FileNotFoundError(f"Cleaned dataset not found: {PROCESSED_CSV}")
    return pd.read_csv(PROCESSED_CSV)


def build_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    feature_cols = [
        "area_type",
        "location",
        "availability",
        "total_sqft",
        "bhk",
        "bath",
        "balcony",
    ]
    missing = [c for c in feature_cols + ["price"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    data = df[feature_cols + ["price"]].copy()
    data = data.dropna(subset=["area_type", "location", "total_sqft", "bhk", "bath", "price"])
    X = data[feature_cols]
    y = data["price"].astype(float)
    final_model_features = [
        "area_type",
        "location",
        "total_sqft",
        "bhk",
        "bath",
        "balcony",
        "is_ready_to_move",
    ]
    return X, y, final_model_features


def make_preprocessor() -> ColumnTransformer:
    numeric_features = ["total_sqft", "bhk", "bath", "balcony", "is_ready_to_move"]
    categorical_features = ["area_type"]

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    location_pipe = Pipeline(
        steps=[
            ("rare", RareLocationGrouper(min_count=RARE_LOCATION_MIN_COUNT)),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    area_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_features),
            ("area", area_pipe, categorical_features),
            ("loc", location_pipe, ["location"]),
        ],
        remainder="drop",
    )


def make_full_pipeline(estimator: BaseEstimator) -> Pipeline:
    return Pipeline(
        steps=[
            ("features", FeatureBuilder()),
            ("preprocess", make_preprocessor()),
            ("model", clone(estimator)),
        ]
    )


def get_candidate_models() -> dict[str, BaseEstimator]:
    return {
        "LinearRegression": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_leaf=2,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_depth=8,
            learning_rate=0.06,
            max_iter=300,
            random_state=RANDOM_STATE,
        ),
    }


def evaluate_cv(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict:
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(
        pipeline,
        X,
        y,
        cv=cv,
        scoring={
            "mae": "neg_mean_absolute_error",
            "rmse": "neg_root_mean_squared_error",
            "r2": "r2",
        },
        n_jobs=-1,
    )
    return {
        "cv_mae_mean": float(-scores["test_mae"].mean()),
        "cv_mae_std": float(scores["test_mae"].std()),
        "cv_rmse_mean": float(-scores["test_rmse"].mean()),
        "cv_rmse_std": float(scores["test_rmse"].std()),
        "cv_r2_mean": float(scores["test_r2"].mean()),
        "cv_r2_std": float(scores["test_r2"].std()),
    }


def residual_range_from_oof(pipeline: Pipeline, X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    oof = cross_val_predict(pipeline, X_train, y_train, cv=cv, n_jobs=-1)
    residuals = y_train.to_numpy(dtype=float) - oof
    low = float(np.percentile(residuals, 10))
    high = float(np.percentile(residuals, 90))
    return {
        "method": "out_of_fold_residual_percentiles",
        "description": (
            "Estimated price range based on model prediction error using "
            "10th/90th percentiles of out-of-fold residuals on the training set. "
            "This is not a statistical confidence interval."
        ),
        "residual_p10_lakhs": low,
        "residual_p90_lakhs": high,
        "mae_oof_lakhs": float(mean_absolute_error(y_train, oof)),
        "supported": True,
    }


def main() -> None:
    DATA_ML_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading cleaned property dataset...")
    df = load_dataset()
    X, y, final_features = build_xy(df)
    print(f"Usable rows for modeling: {len(X):,}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )
    print(f"Train size: {len(X_train):,} | Test size: {len(X_test):,}")

    comparison_rows = []
    cv_results = {}
    for name, estimator in get_candidate_models().items():
        print(f"Cross-validating {name}...")
        pipe = make_full_pipeline(estimator)
        metrics = evaluate_cv(pipe, X_train, y_train)
        cv_results[name] = metrics
        comparison_rows.append({"model": name, **metrics})
        print(
            f"  CV MAE={metrics['cv_mae_mean']:.3f}±{metrics['cv_mae_std']:.3f} | "
            f"RMSE={metrics['cv_rmse_mean']:.3f} | R2={metrics['cv_r2_mean']:.4f}"
        )

    comparison_df = pd.DataFrame(comparison_rows).sort_values("cv_mae_mean")
    comparison_path = DATA_ML_DIR / "model_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)

    selected_name = str(comparison_df.iloc[0]["model"])
    print(f"Selected model by CV MAE: {selected_name}")

    selected_estimator = get_candidate_models()[selected_name]
    final_pipeline = make_full_pipeline(selected_estimator)

    print("Computing residual-based estimate range from training OOF predictions...")
    range_info = residual_range_from_oof(clone(final_pipeline), X_train, y_train)

    print("Fitting selected model on full training set...")
    final_pipeline.fit(X_train, y_train)

    y_pred_test = final_pipeline.predict(X_test)
    test_metrics = {
        "mae": float(mean_absolute_error(y_test, y_pred_test)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
        "r2": float(r2_score(y_test, y_pred_test)),
    }
    print(
        f"Final TEST MAE={test_metrics['mae']:.3f} | "
        f"RMSE={test_metrics['rmse']:.3f} | R2={test_metrics['r2']:.4f}"
    )

    print("Computing feature importance...")
    sample_n = min(2000, len(X_train))
    X_sample = X_train.sample(n=sample_n, random_state=RANDOM_STATE)
    y_sample = y_train.loc[X_sample.index]
    perm = permutation_importance(
        final_pipeline,
        X_sample,
        y_sample,
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )

    feature_names = [
        str(n)
        for n in final_pipeline.named_steps["preprocess"].get_feature_names_out()
    ]
    model = final_pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        native = np.asarray(model.feature_importances_, dtype=float)
        source = "native_feature_importances_"
    elif hasattr(model, "coef_"):
        native = np.abs(np.asarray(model.coef_, dtype=float).ravel())
        source = "abs_coefficients"
    else:
        native = np.zeros(len(feature_names))
        source = "unavailable"

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance_native": native,
            "importance_source": source,
        }
    ).sort_values("importance_native", ascending=False)
    importance_df.to_csv(DATA_ML_DIR / "feature_importance.csv", index=False)

    raw_feature_order = list(X_train.columns)
    raw_perm_rows = [
        {
            "raw_feature": raw_feature_order[i],
            "permutation_importance_mae": float(perm.importances_mean[i]),
        }
        for i in range(len(raw_feature_order))
    ]
    pd.DataFrame(raw_perm_rows).sort_values(
        "permutation_importance_mae", ascending=False
    ).to_csv(
        DATA_ML_DIR / "permutation_importance_raw_features.csv",
        index=False,
    )

    global_feature_influence = build_global_feature_influence(
        [
            (row["raw_feature"], row["permutation_importance_mae"])
            for row in raw_perm_rows
        ]
    )
    global_feature_influence["source_csv"] = (
        "data/ml/permutation_importance_raw_features.csv"
    )

    sample_rows = X_test.head(3).copy()
    sample_preds = final_pipeline.predict(sample_rows)
    unseen = sample_rows.iloc[[0]].copy()
    unseen.loc[:, "location"] = "Completely Unknown Layout XYZ"
    unseen_pred = float(final_pipeline.predict(unseen)[0])

    print("Saving model artifacts...")
    joblib.dump(final_pipeline, MODEL_PATH)

    metadata = {
        "model_name": selected_name,
        "model_version": MODEL_VERSION,
        "training_date_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_name": "bengaluru_property_clean.csv",
        "dataset_path": str(PROCESSED_CSV),
        "dataset_row_count_total_clean": int(len(df)),
        "dataset_row_count_model_usable": int(len(X)),
        "feature_names_raw": list(X.columns),
        "feature_names_model": final_features,
        "excluded_features": [
            "price_per_sqft",
            "society",
            "raw availability date categories",
            "market_area / market history features",
        ],
        "target_name": "price",
        "target_unit": "INR_lakhs",
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "random_state": RANDOM_STATE,
        "rare_location_min_count": RARE_LOCATION_MIN_COUNT,
        "cv_metrics": cv_results,
        "selected_model_cv_metrics": cv_results[selected_name],
        "final_test_metrics": test_metrics,
        "selection_rule": "Lowest cross-validated MAE on training folds",
        "prediction_range": range_info,
        "sample_predictions_lakhs": [float(x) for x in sample_preds],
        "unseen_location_smoke_prediction_lakhs": unseen_pred,
        "artifact_paths": {
            "model": str(MODEL_PATH),
            "metadata": str(METADATA_PATH),
            "comparison_csv": str(comparison_path),
        },
        "limitations": [
            "Predictions are model estimates from historical listing-style data, not professional valuations.",
            "Target unit is INR lakhs.",
            "price_per_sqft is excluded to prevent target leakage.",
            "Market-history dataset is not used in training.",
            "Rare localities are grouped as Other; estimates for sparse areas are less reliable.",
            "No property transaction date was available for time-aware validation.",
            "Estimated price range is residual-based and is not a confidence interval.",
            "Feature influence is global model-level permutation importance, not a local rupee attribution for an individual estimate.",
        ],
        "global_feature_influence": global_feature_influence,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    evaluation = {
        "selected_model": selected_name,
        "selection_metric": "cv_mae_mean",
        "cv_results": cv_results,
        "final_test_metrics": test_metrics,
        "prediction_range": range_info,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
    }
    (DATA_ML_DIR / "model_evaluation.json").write_text(
        json.dumps(evaluation, indent=2), encoding="utf-8"
    )

    feature_summary = {
        "target": {"name": "price", "unit": "INR_lakhs"},
        "input_features": final_features,
        "raw_columns_used": list(X.columns),
        "preprocessing": {
            "numeric": ["total_sqft", "bhk", "bath", "balcony", "is_ready_to_move"],
            "categorical": ["area_type", "location"],
            "location_rare_min_count": RARE_LOCATION_MIN_COUNT,
            "location_unknown_handling": "OneHotEncoder(handle_unknown='ignore')",
            "balcony_imputation": "median",
            "availability_handling": "binary is_ready_to_move",
        },
        "leakage_exclusions": ["price_per_sqft"],
        "transformed_feature_count": len(feature_names),
    }
    (DATA_ML_DIR / "feature_summary.json").write_text(
        json.dumps(feature_summary, indent=2), encoding="utf-8"
    )

    print("TRAINING_COMPLETE")
    print(f"SELECTED_MODEL={selected_name}")
    print(f"TEST_MAE={test_metrics['mae']:.4f}")
    print(f"TEST_RMSE={test_metrics['rmse']:.4f}")
    print(f"TEST_R2={test_metrics['r2']:.4f}")
    print(f"MODEL_PATH={MODEL_PATH}")
    print(f"UNSEEN_LOC_PRED={unseen_pred:.4f}")


if __name__ == "__main__":
    main()
