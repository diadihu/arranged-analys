from __future__ import annotations

import pandas as pd


def build_basic_features(df: pd.DataFrame, digit_count: int) -> pd.DataFrame:
    digit_columns = [f"d{i}" for i in range(1, digit_count + 1)]
    missing = [column for column in digit_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing digit columns: {missing}")

    feature_df = df.copy()
    feature_df["sum_value"] = feature_df[digit_columns].sum(axis=1)
    feature_df["span_value"] = feature_df[digit_columns].max(axis=1) - feature_df[digit_columns].min(axis=1)
    feature_df["odd_count"] = feature_df[digit_columns].apply(lambda row: int((row % 2).sum()), axis=1)
    feature_df["large_count"] = feature_df[digit_columns].apply(lambda row: int((row >= 5).sum()), axis=1)
    feature_df["unique_digits"] = feature_df[digit_columns].nunique(axis=1)
    return feature_df
