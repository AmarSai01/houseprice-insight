"""Reusable sklearn transformers for the house-price model pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class FeatureBuilder(BaseEstimator, TransformerMixin):
    """Create model-ready columns from the cleaned property dataframe."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        df = pd.DataFrame(X).copy()
        avail = df.get("availability", pd.Series(index=df.index, dtype=object))
        df["is_ready_to_move"] = (
            avail.astype(str).str.strip().str.lower().eq("ready to move").astype(int)
        )
        loc = df.get("location", pd.Series(index=df.index, dtype=object))
        df["location"] = (
            loc.astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.strip(" ,;")
        )
        return df


class RareLocationGrouper(BaseEstimator, TransformerMixin):
    """Group rare locations into Other using frequencies from training data only."""

    def __init__(self, min_count: int = 10, other_label: str = "Other"):
        self.min_count = min_count
        self.other_label = other_label
        self.frequent_locations_ = set()

    def fit(self, X, y=None):
        series = pd.Series(np.asarray(X).ravel())
        counts = series.value_counts(dropna=False)
        self.frequent_locations_ = set(counts[counts >= self.min_count].index.astype(str))
        return self

    def transform(self, X):
        series = pd.Series(np.asarray(X).ravel()).astype(str)
        grouped = series.where(series.isin(self.frequent_locations_), self.other_label)
        return grouped.to_frame(name="location")

    def get_feature_names_out(self, input_features=None):
        return np.array(["location"], dtype=object)
