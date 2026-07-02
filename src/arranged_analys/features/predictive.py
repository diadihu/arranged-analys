from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Sequence

import numpy as np

from arranged_analys.data.sporttery import DrawRecord, LOTTERY_CONFIG


@dataclass(slots=True)
class FeatureConfig:
    name: str
    lag_depth: int
    rolling_windows: tuple[int, ...]


@dataclass(slots=True)
class SupervisedDataset:
    lottery_type: str
    feature_config: FeatureConfig
    feature_names: list[str]
    X: np.ndarray
    y: np.ndarray
    sample_issues: list[str]


DEFAULT_FEATURE_CONFIGS = (
    FeatureConfig(name="lag6_win5_10_20", lag_depth=6, rolling_windows=(5, 10, 20)),
    FeatureConfig(name="lag10_win5_10_20_30", lag_depth=10, rolling_windows=(5, 10, 20, 30)),
)


def build_supervised_dataset(
    records: Sequence[DrawRecord],
    lottery_type: str,
    feature_config: FeatureConfig,
) -> SupervisedDataset:
    digit_count = int(LOTTERY_CONFIG[lottery_type]["digit_count"])
    min_history = max(feature_config.lag_depth, max(feature_config.rolling_windows))
    if len(records) <= min_history:
        raise ValueError(f"Not enough records for feature config {feature_config.name}")

    feature_names: list[str] = []
    feature_rows: list[list[float]] = []
    targets: list[list[int]] = []
    sample_issues: list[str] = []

    for target_index in range(min_history, len(records)):
        feature_row, row_feature_names = build_feature_row(
            records[:target_index],
            lottery_type=lottery_type,
            feature_config=feature_config,
        )
        if not feature_names:
            feature_names = row_feature_names
        feature_rows.append(feature_row)
        targets.append(records[target_index].digits[:digit_count])
        sample_issues.append(records[target_index].issue)

    return SupervisedDataset(
        lottery_type=lottery_type,
        feature_config=feature_config,
        feature_names=feature_names,
        X=np.asarray(feature_rows, dtype=np.float32),
        y=np.asarray(targets, dtype=np.int64),
        sample_issues=sample_issues,
    )


def build_next_feature_row(
    records: Sequence[DrawRecord],
    lottery_type: str,
    feature_config: FeatureConfig,
) -> tuple[np.ndarray, list[str]]:
    feature_row, feature_names = build_feature_row(
        records,
        lottery_type=lottery_type,
        feature_config=feature_config,
    )
    return np.asarray(feature_row, dtype=np.float32), feature_names


def build_feature_row(
    history: Sequence[DrawRecord],
    lottery_type: str,
    feature_config: FeatureConfig,
) -> tuple[list[float], list[str]]:
    digit_count = int(LOTTERY_CONFIG[lottery_type]["digit_count"])
    min_history = max(feature_config.lag_depth, max(feature_config.rolling_windows))
    if len(history) < min_history:
        raise ValueError(f"Need at least {min_history} records to build features.")

    feature_values: list[float] = []
    feature_names: list[str] = []

    for lag in range(1, feature_config.lag_depth + 1):
        record = history[-lag]
        stats = _draw_stats(record.digits[:digit_count])
        for position, digit in enumerate(record.digits[:digit_count], start=1):
            feature_names.append(f"lag_{lag}_d{position}")
            feature_values.append(float(digit))
        for name, value in stats.items():
            feature_names.append(f"lag_{lag}_{name}")
            feature_values.append(float(value))

    for window in feature_config.rolling_windows:
        window_records = history[-window:]
        per_position_frequencies = _position_digit_frequencies(window_records, digit_count)
        overall_counter = Counter()
        sums: list[float] = []
        spans: list[float] = []
        odd_counts: list[float] = []
        large_counts: list[float] = []
        unique_counts: list[float] = []
        repeat_counts: list[float] = []

        previous_digits: list[int] | None = None
        for record in window_records:
            digits = record.digits[:digit_count]
            stats = _draw_stats(digits)
            overall_counter.update(digits)
            sums.append(float(stats["sum_value"]))
            spans.append(float(stats["span_value"]))
            odd_counts.append(float(stats["odd_count"]))
            large_counts.append(float(stats["large_count"]))
            unique_counts.append(float(stats["unique_digits"]))
            if previous_digits is not None:
                repeat_counts.append(float(sum(int(a == b) for a, b in zip(previous_digits, digits))))
            previous_digits = digits

        for position in range(digit_count):
            for digit in range(10):
                feature_names.append(f"window_{window}_pos_{position + 1}_digit_{digit}_ratio")
                feature_values.append(per_position_frequencies[position][digit] / window)

                feature_names.append(f"window_{window}_pos_{position + 1}_digit_{digit}_gap")
                feature_values.append(float(_digit_gap(window_records, position, digit)))

        for digit in range(10):
            feature_names.append(f"window_{window}_overall_digit_{digit}_ratio")
            feature_values.append(overall_counter[digit] / (window * digit_count))

        feature_names.extend(
            [
                f"window_{window}_mean_sum",
                f"window_{window}_std_sum",
                f"window_{window}_mean_span",
                f"window_{window}_mean_odd_count",
                f"window_{window}_mean_large_count",
                f"window_{window}_mean_unique_digits",
                f"window_{window}_mean_repeat_with_prev",
            ]
        )
        feature_values.extend(
            [
                _safe_mean(sums),
                _safe_std(sums),
                _safe_mean(spans),
                _safe_mean(odd_counts),
                _safe_mean(large_counts),
                _safe_mean(unique_counts),
                _safe_mean(repeat_counts),
            ]
        )

    latest_digits = history[-1].digits[:digit_count]
    latest_sum = sum(latest_digits)
    latest_span = max(latest_digits) - min(latest_digits)
    feature_names.extend(
        [
            "latest_sum_tail",
            "latest_span",
            "latest_even_odd_balance",
            "latest_large_small_balance",
            "latest_zero_count",
        ]
    )
    feature_values.extend(
        [
            float(latest_sum % 10),
            float(latest_span),
            float(sum(1 for digit in latest_digits if digit % 2 == 0) - sum(1 for digit in latest_digits if digit % 2 == 1)),
            float(sum(1 for digit in latest_digits if digit >= 5) - sum(1 for digit in latest_digits if digit < 5)),
            float(sum(1 for digit in latest_digits if digit == 0)),
        ]
    )

    return feature_values, feature_names


def _draw_stats(digits: Sequence[int]) -> dict[str, float]:
    sum_value = float(sum(digits))
    span_value = float(max(digits) - min(digits))
    odd_count = float(sum(1 for digit in digits if digit % 2 == 1))
    large_count = float(sum(1 for digit in digits if digit >= 5))
    unique_digits = float(len(set(digits)))
    return {
        "sum_value": sum_value,
        "span_value": span_value,
        "odd_count": odd_count,
        "large_count": large_count,
        "unique_digits": unique_digits,
    }


def _position_digit_frequencies(records: Iterable[DrawRecord], digit_count: int) -> list[Counter]:
    counters = [Counter() for _ in range(digit_count)]
    for record in records:
        for position, digit in enumerate(record.digits[:digit_count]):
            counters[position][digit] += 1
    return counters


def _digit_gap(records: Sequence[DrawRecord], position: int, digit: int) -> int:
    for gap, record in enumerate(reversed(records), start=1):
        if record.digits[position] == digit:
            return gap
    return len(records) + 1


def _safe_mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _safe_std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _safe_mean(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return float(sqrt(variance))
