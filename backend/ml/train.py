"""
ML Training Pipeline for House Price Prediction
Trains a RandomForestRegressor model and saves it along with preprocessing pipeline.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
import pickle
import os
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Absolute locations derived from this file (backend/ml/train.py)
ML_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ML_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DATASET = PROJECT_ROOT / "data" / "house_data.csv"


def resolve_dataset_path(csv_path: str | None = None) -> Path:
    """
    Resolve the dataset path whether the process is started from the project
    root or from the backend directory.
    """
    candidates = []
    if csv_path:
        path = Path(csv_path)
        candidates.append(path)
        if not path.is_absolute():
            candidates.append(Path.cwd() / path)
            candidates.append(PROJECT_ROOT / path)
            candidates.append(BACKEND_DIR / path)
            # Allow bare filename
            candidates.append(PROJECT_ROOT / "data" / path.name)
            candidates.append(BACKEND_DIR / "data" / path.name)

    candidates.append(DEFAULT_DATASET)

    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    raise FileNotFoundError(
        f"Dataset not found. Tried: {csv_path!r}. Expected at {DEFAULT_DATASET}"
    )


def load_data(csv_path: str) -> pd.DataFrame:
    """Load house price dataset from CSV file."""
    resolved = resolve_dataset_path(csv_path)
    df = pd.read_csv(resolved)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the dataset: handle missing values, remove duplicates, etc."""
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Remove rows with missing price (target variable)
    df = df.dropna(subset=['price'])
    
    # Handle missing values in numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col != 'price':
            df[col].fillna(df[col].median(), inplace=True)
    
    # Handle missing values in categorical columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown', inplace=True)
    
    return df


def create_preprocessing_pipeline(df: pd.DataFrame) -> tuple:
    """
    Create preprocessing pipeline for features.
    Returns: (preprocessor, feature_columns)
    Note: This function is kept for compatibility but encoding is done separately.
    """
    # Identify feature columns (exclude target)
    feature_cols = [col for col in df.columns if col != 'price']
    
    # Separate numeric and categorical columns
    numeric_features = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = df[feature_cols].select_dtypes(include=['object']).columns.tolist()
    
    return None, feature_cols, numeric_features, categorical_features


def encode_categorical_features(df: pd.DataFrame, categorical_features: list, fit: bool = True, encoders: dict = None) -> tuple:
    """
    Encode categorical features using LabelEncoder.
    Returns: (encoded_df, encoders_dict)
    """
    df_encoded = df.copy()
    
    if encoders is None:
        encoders = {}
    
    for col in categorical_features:
        if col in df_encoded.columns:
            if fit:
                le = LabelEncoder()
                df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
                encoders[col] = le
            else:
                if col in encoders:
                    # Handle unseen categories
                    le = encoders[col]
                    unique_values = set(df_encoded[col].astype(str).unique())
                    known_classes = set(le.classes_)
                    unknown = unique_values - known_classes
                    
                    if unknown:
                        # Map unknown to a default value
                        df_encoded[col] = df_encoded[col].astype(str).replace(list(unknown), le.classes_[0])
                    df_encoded[col] = le.transform(df_encoded[col].astype(str))
                else:
                    # If encoder not found, use simple integer encoding
                    df_encoded[col] = pd.Categorical(df_encoded[col]).codes
    
    return df_encoded, encoders


def train_model(csv_path: str = None, model_dir: str = None):
    """
    Main training function.
    Loads data, preprocesses, trains model, and saves everything.

    Model artifacts are ALWAYS written to backend/ml/ next to this module,
    independent of the current working directory. The model_dir argument is
    accepted for compatibility but ignored so the location stays consistent.
    """
    dataset_path = resolve_dataset_path(csv_path)
    # Always save beside this file: backend/ml/{model,preprocess}.pkl
    model_dir_path = ML_DIR
    if model_dir is not None and Path(model_dir).resolve() != model_dir_path:
        print(
            f"Note: ignoring model_dir={model_dir!r}; "
            f"saving to canonical location {model_dir_path}"
        )

    print("Loading dataset...")
    print(f"Dataset path: {dataset_path}")
    df = load_data(str(dataset_path))
    print(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns")
    
    print("Cleaning data...")
    df = clean_data(df)
    print(f"After cleaning: {len(df)} rows")
    
    # Get feature columns
    feature_cols = [col for col in df.columns if col != 'price']
    numeric_features = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = df[feature_cols].select_dtypes(include=['object']).columns.tolist()
    
    print(f"Numeric features: {numeric_features}")
    print(f"Categorical features: {categorical_features}")
    
    # Encode categorical features
    print("Encoding categorical features...")
    df_encoded, encoders = encode_categorical_features(df, categorical_features, fit=True)
    
    # Prepare features and target
    X = df_encoded[feature_cols]
    y = df_encoded['price']
    
    # Split data
    print("Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Scale numeric features
    print("Scaling numeric features...")
    scaler = StandardScaler()
    X_train_scaled = X_train.copy()
    X_test_scaled = X_test.copy()
    
    if numeric_features:
        X_train_scaled[numeric_features] = scaler.fit_transform(X_train[numeric_features])
        X_test_scaled[numeric_features] = scaler.transform(X_test[numeric_features])
    
    # Train model
    print("Training RandomForestRegressor...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate model
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)
    
    train_mae = mean_absolute_error(y_train, y_pred_train)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    
    print("\n=== Model Performance ===")
    print(f"Train MAE: {train_mae:.2f}")
    print(f"Test MAE: {test_mae:.2f}")
    print(f"Train RMSE: {train_rmse:.2f}")
    print(f"Test RMSE: {test_rmse:.2f}")
    print(f"Train R²: {train_r2:.4f}")
    print(f"Test R²: {test_r2:.4f}")
    
    # Save model and preprocessing components to backend/ml/
    model_dir_path.mkdir(parents=True, exist_ok=True)

    model_path = model_dir_path / "model.pkl"
    preprocess_path = model_dir_path / "preprocess.pkl"

    print(f"\nSaving model to {model_path}...")
    print(f"Saving preprocessing to {preprocess_path}...")

    # Save model
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Save preprocessing components
    preprocess_data = {
        "scaler": scaler,
        "encoders": encoders,
        "feature_columns": feature_cols,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "metrics": {
            "train_mae": float(train_mae),
            "test_mae": float(test_mae),
            "train_rmse": float(train_rmse),
            "test_rmse": float(test_rmse),
            "train_r2": float(train_r2),
            "test_r2": float(test_r2),
        },
    }

    with open(preprocess_path, "wb") as f:
        pickle.dump(preprocess_data, f)

    print("Model and preprocessing pipeline saved successfully!")
    print(f"Model file: {model_path}")
    print(f"Preprocess file: {preprocess_path}")

    return model, preprocess_data, {
        "train_mae": train_mae,
        "test_mae": test_mae,
        "train_rmse": train_rmse,
        "test_rmse": test_rmse,
        "train_r2": train_r2,
        "test_r2": test_r2,
    }


if __name__ == "__main__":
    import sys

    csv_arg = sys.argv[1] if len(sys.argv) > 1 else None
    train_model(csv_arg)

