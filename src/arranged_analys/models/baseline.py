from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class BaselinePrediction:
    lottery_type: str
    window_size: int
    predicted_digits: list[int]
    digit_frequencies: dict[str, dict[int, int]]


def predict_by_recent_frequency(
    df: pd.DataFrame,
    lottery_type: str,
    digit_count: int,
    window_size: int = 200,
) -> BaselinePrediction:
    if df.empty:
        raise ValueError("Input data frame is empty.")

    digit_columns = [f"d{i}" for i in range(1, digit_count + 1)]
    recent = df.tail(window_size)
    predicted_digits: list[int] = []
    digit_frequencies: dict[str, dict[int, int]] = {}

    for column in digit_columns:
        counts = recent[column].dropna().astype(int).value_counts().sort_values(ascending=False)
        if counts.empty:
            raise ValueError(f"Column {column} has no valid digits.")
        predicted_digits.append(int(counts.index[0]))
        digit_frequencies[column] = {int(index): int(value) for index, value in counts.items()}

    return BaselinePrediction(
        lottery_type=lottery_type,
        window_size=min(window_size, len(df)),
        predicted_digits=predicted_digits,
        digit_frequencies=digit_frequencies,
    )
