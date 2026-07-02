from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import product
from math import exp, log
from typing import Callable, Sequence

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from arranged_analys.data.sporttery import DrawRecord, LOTTERY_CONFIG
from arranged_analys.features.predictive import (
    DEFAULT_FEATURE_CONFIGS,
    FeatureConfig,
    SupervisedDataset,
    build_next_feature_row,
    build_supervised_dataset,
)

MAX_BENCHMARK_SAMPLES = 720


@dataclass(slots=True)
class BenchmarkMetrics:
    mean_position_hits: float
    position_accuracy: float
    exact_match_rate: float
    mean_digit_overlap: float
    at_least_one_hit_rate: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class ModelBenchmark:
    model_name: str
    feature_config: str
    cv_metrics: BenchmarkMetrics
    holdout_metrics: BenchmarkMetrics
    holdout_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "feature_config": self.feature_config,
            "cv_metrics": self.cv_metrics.to_dict(),
            "holdout_metrics": self.holdout_metrics.to_dict(),
            "holdout_size": self.holdout_size,
        }


@dataclass(slots=True)
class PositionProbability:
    digit: int
    probability: float

    def to_dict(self) -> dict[str, float | int]:
        return {"digit": self.digit, "probability": self.probability}


@dataclass(slots=True)
class RuleProfile:
    danma_digits: list[int]
    dudan_digits: list[int]
    preferred_sum_tails: list[int]
    filtered_sum_tails: list[int]

    def to_dict(self) -> dict[str, list[int]]:
        return asdict(self)


@dataclass(slots=True)
class RankedCombination:
    number: str
    combined_score: float
    ml_probability: float
    frequency_score: float
    rule_score: float
    explanation: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkSelectionResult:
    lottery_type: str
    feature_config: FeatureConfig
    best_model_name: str
    benchmarks: list[ModelBenchmark]
    holdout_size: int
    position_probabilities: list[list[PositionProbability]]
    rule_profile: RuleProfile
    ranked_combinations: list[RankedCombination]
    best_metrics: BenchmarkMetrics

    def to_dict(self) -> dict[str, object]:
        return {
            "lottery_type": self.lottery_type,
            "feature_config": asdict(self.feature_config),
            "best_model_name": self.best_model_name,
            "holdout_size": self.holdout_size,
            "benchmarks": [benchmark.to_dict() for benchmark in self.benchmarks],
            "best_metrics": self.best_metrics.to_dict(),
            "position_probabilities": [
                [item.to_dict() for item in position_items]
                for position_items in self.position_probabilities
            ],
            "rule_profile": self.rule_profile.to_dict(),
            "ranked_combinations": [item.to_dict() for item in self.ranked_combinations],
        }


def run_benchmark_selection(
    records: Sequence[DrawRecord],
    lottery_type: str,
    feature_configs: Sequence[FeatureConfig] = DEFAULT_FEATURE_CONFIGS,
) -> BenchmarkSelectionResult:
    digit_count = int(LOTTERY_CONFIG[lottery_type]["digit_count"])
    benchmarks: list[ModelBenchmark] = []
    best_choice: tuple[FeatureConfig, str, BenchmarkMetrics] | None = None

    for feature_config in feature_configs:
        dataset = build_supervised_dataset(
            _truncate_records_for_features(records, feature_config, max_samples=MAX_BENCHMARK_SAMPLES),
            lottery_type,
            feature_config,
        )
        holdout_size = _determine_holdout_size(len(dataset.X))
        if len(dataset.X) <= holdout_size + 400:
            raise ValueError("Dataset is too small for robust benchmark splits.")

        for model_name in model_factories():
            cv_metrics, holdout_metrics = _benchmark_single_model(dataset, model_name, holdout_size)
            benchmark = ModelBenchmark(
                model_name=model_name,
                feature_config=feature_config.name,
                cv_metrics=cv_metrics,
                holdout_metrics=holdout_metrics,
                holdout_size=holdout_size,
            )
            benchmarks.append(benchmark)
            candidate_choice = (feature_config, model_name, holdout_metrics)
            if best_choice is None or _is_better_metrics(holdout_metrics, best_choice[2]):
                best_choice = candidate_choice

    assert best_choice is not None
    best_feature_config, best_model_name, best_metrics = best_choice
    best_dataset = build_supervised_dataset(
        _truncate_records_for_features(records, best_feature_config, max_samples=MAX_BENCHMARK_SAMPLES),
        lottery_type,
        best_feature_config,
    )
    holdout_size = _determine_holdout_size(len(best_dataset.X))
    next_row, _ = build_next_feature_row(records, lottery_type, best_feature_config)
    trained_models = _fit_position_models(
        model_name=best_model_name,
        X=best_dataset.X,
        y=best_dataset.y,
    )
    position_probabilities = _predict_position_probabilities(
        trained_models=trained_models,
        feature_row=next_row.reshape(1, -1),
        digit_count=digit_count,
    )
    rule_profile = build_rule_profile(records, digit_count=digit_count)
    ranked_combinations = rank_combinations(
        records=records,
        lottery_type=lottery_type,
        position_probabilities=position_probabilities,
        rule_profile=rule_profile,
    )
    return BenchmarkSelectionResult(
        lottery_type=lottery_type,
        feature_config=best_feature_config,
        best_model_name=best_model_name,
        benchmarks=sorted(
            benchmarks,
            key=lambda item: (
                -item.holdout_metrics.mean_position_hits,
                -item.holdout_metrics.exact_match_rate,
                -item.holdout_metrics.mean_digit_overlap,
                item.model_name,
            ),
        ),
        holdout_size=holdout_size,
        position_probabilities=position_probabilities,
        rule_profile=rule_profile,
        ranked_combinations=ranked_combinations,
        best_metrics=best_metrics,
    )


def build_rule_profile(records: Sequence[DrawRecord], digit_count: int) -> RuleProfile:
    recent_window = 40
    sum_tail_window = 120
    recent_records = records[-recent_window:]
    tail_records = records[-sum_tail_window:]

    overall_counter = Counter()
    for record in recent_records:
        overall_counter.update(record.digits[:digit_count])
    ordered_digits = [digit for digit, _ in overall_counter.most_common()]
    if len(ordered_digits) < 10:
        ordered_digits.extend(digit for digit in range(10) if digit not in ordered_digits)

    danma_count = 4 if digit_count == 3 else 5
    dudan_count = 2 if digit_count == 3 else 3
    danma_digits = ordered_digits[:danma_count]
    dudan_digits = list(reversed(ordered_digits))[:dudan_count]

    sum_tail_counter = Counter(sum(record.digits[:digit_count]) % 10 for record in tail_records)
    ordered_tails = [digit for digit, _ in sum_tail_counter.most_common()]
    ordered_tails.extend(digit for digit in range(10) if digit not in ordered_tails)
    preferred_sum_tails = ordered_tails[:4]
    filtered_sum_tails = list(reversed(ordered_tails))[:2]
    return RuleProfile(
        danma_digits=danma_digits,
        dudan_digits=dudan_digits,
        preferred_sum_tails=preferred_sum_tails,
        filtered_sum_tails=filtered_sum_tails,
    )


def rank_combinations(
    records: Sequence[DrawRecord],
    lottery_type: str,
    position_probabilities: list[list[PositionProbability]],
    rule_profile: RuleProfile,
) -> list[RankedCombination]:
    digit_count = int(LOTTERY_CONFIG[lottery_type]["digit_count"])
    top_k_per_position = 4 if digit_count == 3 else 3
    recent_window = min(120, len(records))
    recent_records = records[-recent_window:]
    frequency_lookup = _build_frequency_lookup(recent_records, digit_count)
    latest_digits = records[-1].digits[:digit_count]

    candidate_groups = [position_items[:top_k_per_position] for position_items in position_probabilities]
    combinations: list[RankedCombination] = []
    for group in product(*candidate_groups):
        digits = [item.digit for item in group]
        number = "".join(str(digit) for digit in digits)
        ml_probability = 1.0
        frequency_score = 0.0
        for position, item in enumerate(group):
            ml_probability *= item.probability
            frequency_score += frequency_lookup[position][item.digit]
        frequency_score /= digit_count

        rule_score, explanation = _score_rules(digits, latest_digits, rule_profile)
        ml_component = exp(sum(log(max(item.probability, 1e-8)) for item in group) / digit_count)
        combined_score = round((0.6 * ml_component) + (0.25 * frequency_score) + (0.15 * rule_score), 6)
        combinations.append(
            RankedCombination(
                number=number,
                combined_score=combined_score,
                ml_probability=round(ml_probability, 8),
                frequency_score=round(frequency_score, 6),
                rule_score=round(rule_score, 6),
                explanation=explanation,
            )
        )

    combinations.sort(key=lambda item: (-item.combined_score, -item.ml_probability, item.number))
    return combinations[:12]


def _benchmark_single_model(
    dataset: SupervisedDataset,
    model_name: str,
    holdout_size: int,
) -> tuple[BenchmarkMetrics, BenchmarkMetrics]:
    X = dataset.X
    y = dataset.y
    train_X = X[:-holdout_size]
    train_y = y[:-holdout_size]
    holdout_X = X[-holdout_size:]
    holdout_y = y[-holdout_size:]

    fold_metrics: list[BenchmarkMetrics] = []
    for train_idx, val_idx in _time_series_splits(
        len(train_X),
        n_splits=3,
        validation_size=max(60, holdout_size // 2),
    ):
        models = _fit_position_models(model_name, train_X[train_idx], train_y[train_idx])
        predictions = _predict_positions(models, train_X[val_idx])
        fold_metrics.append(_compute_metrics(train_y[val_idx], predictions))

    cv_metrics = _average_metrics(fold_metrics)
    holdout_models = _fit_position_models(model_name, train_X, train_y)
    holdout_predictions = _predict_positions(holdout_models, holdout_X)
    holdout_metrics = _compute_metrics(holdout_y, holdout_predictions)
    return cv_metrics, holdout_metrics


def _fit_position_models(model_name: str, X: np.ndarray, y: np.ndarray) -> list[object]:
    models: list[object] = []
    factory = model_factories()[model_name]
    for position in range(y.shape[1]):
        model = clone(factory())
        model.fit(X, y[:, position])
        models.append(model)
    return models


def _predict_positions(models: Sequence[object], X: np.ndarray) -> np.ndarray:
    predicted_columns = [model.predict(X) for model in models]
    return np.column_stack(predicted_columns)


def _predict_position_probabilities(
    trained_models: Sequence[object],
    feature_row: np.ndarray,
    digit_count: int,
) -> list[list[PositionProbability]]:
    probabilities: list[list[PositionProbability]] = []
    for position in range(digit_count):
        model = trained_models[position]
        prob = model.predict_proba(feature_row)[0]
        classes = list(getattr(model, "classes_"))
        probability_by_digit = {
            int(digit): round(float(probability), 6)
            for digit, probability in zip(classes, prob)
        }
        items = [
            PositionProbability(digit=digit, probability=probability_by_digit.get(digit, 0.0))
            for digit in range(10)
        ]
        items.sort(key=lambda item: (-item.probability, item.digit))
        probabilities.append(items)
    return probabilities


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> BenchmarkMetrics:
    exact_hits = (y_true == y_pred).sum(axis=1)
    position_accuracy = float((y_true == y_pred).mean())
    mean_position_hits = float(exact_hits.mean())
    exact_match_rate = float(np.mean(exact_hits == y_true.shape[1]))
    at_least_one_hit_rate = float(np.mean(exact_hits >= 1))

    overlap_scores = [_digit_overlap_score(actual, predicted) for actual, predicted in zip(y_true, y_pred)]
    mean_digit_overlap = float(np.mean(overlap_scores))
    return BenchmarkMetrics(
        mean_position_hits=round(mean_position_hits, 6),
        position_accuracy=round(position_accuracy, 6),
        exact_match_rate=round(exact_match_rate, 6),
        mean_digit_overlap=round(mean_digit_overlap, 6),
        at_least_one_hit_rate=round(at_least_one_hit_rate, 6),
    )


def _average_metrics(metrics: Sequence[BenchmarkMetrics]) -> BenchmarkMetrics:
    return BenchmarkMetrics(
        mean_position_hits=round(float(np.mean([item.mean_position_hits for item in metrics])), 6),
        position_accuracy=round(float(np.mean([item.position_accuracy for item in metrics])), 6),
        exact_match_rate=round(float(np.mean([item.exact_match_rate for item in metrics])), 6),
        mean_digit_overlap=round(float(np.mean([item.mean_digit_overlap for item in metrics])), 6),
        at_least_one_hit_rate=round(float(np.mean([item.at_least_one_hit_rate for item in metrics])), 6),
    )


def _digit_overlap_score(actual: Sequence[int], predicted: Sequence[int]) -> float:
    actual_counter = Counter(actual)
    predicted_counter = Counter(predicted)
    overlap = 0
    for digit in range(10):
        overlap += min(actual_counter[digit], predicted_counter[digit])
    return overlap / len(actual)


def _determine_holdout_size(record_count: int) -> int:
    return min(240, max(120, record_count // 12))


def _time_series_splits(
    sample_count: int,
    n_splits: int,
    validation_size: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    minimum_train_size = max(300, validation_size * 2)
    remaining = sample_count - minimum_train_size
    if remaining < validation_size:
        raise ValueError("Not enough data for time-series cross validation.")

    max_splits = min(n_splits, remaining // validation_size)
    for split_index in range(max_splits):
        train_end = minimum_train_size + (split_index * validation_size)
        val_end = train_end + validation_size
        train_idx = np.arange(0, train_end)
        val_idx = np.arange(train_end, min(val_end, sample_count))
        if len(val_idx) == 0:
            continue
        splits.append((train_idx, val_idx))
    return splits


def _is_better_metrics(candidate: BenchmarkMetrics, current: BenchmarkMetrics) -> bool:
    candidate_key = (
        candidate.mean_position_hits,
        candidate.exact_match_rate,
        candidate.mean_digit_overlap,
        candidate.at_least_one_hit_rate,
    )
    current_key = (
        current.mean_position_hits,
        current.exact_match_rate,
        current.mean_digit_overlap,
        current.at_least_one_hit_rate,
    )
    return candidate_key > current_key


def _build_frequency_lookup(records: Sequence[DrawRecord], digit_count: int) -> list[dict[int, float]]:
    lookup: list[dict[int, float]] = []
    for position in range(digit_count):
        counter = Counter(record.digits[position] for record in records)
        total = max(1, sum(counter.values()))
        lookup.append({digit: counter[digit] / total for digit in range(10)})
    return lookup


def _truncate_records_for_features(
    records: Sequence[DrawRecord],
    feature_config: FeatureConfig,
    max_samples: int,
) -> Sequence[DrawRecord]:
    min_history = max(feature_config.lag_depth, max(feature_config.rolling_windows))
    keep_count = max_samples + min_history
    if len(records) <= keep_count:
        return records
    return records[-keep_count:]


def _score_rules(
    digits: Sequence[int],
    latest_digits: Sequence[int],
    rule_profile: RuleProfile,
) -> tuple[float, list[str]]:
    score = 0.5
    explanation: list[str] = []
    sum_tail = sum(digits) % 10

    if any(digit in rule_profile.danma_digits for digit in digits):
        score += 0.2
        explanation.append("包含胆码趋势数字")
    if any(digit in rule_profile.dudan_digits for digit in digits):
        score -= 0.18
        explanation.append("包含低频独胆数字")
    if sum_tail in rule_profile.preferred_sum_tails:
        score += 0.14
        explanation.append("和值尾数匹配近期强势区间")
    if sum_tail in rule_profile.filtered_sum_tails:
        score -= 0.14
        explanation.append("和值尾数落入近期弱势区间")

    same_position_hits = sum(int(left == right) for left, right in zip(digits, latest_digits))
    if same_position_hits >= max(2, len(digits) - 1):
        score -= 0.1
        explanation.append("与最新开奖号码位次重复过多")
    elif same_position_hits == 0:
        score += 0.05
        explanation.append("与最新开奖号码形成错位分散")

    return min(1.0, max(0.0, score)), explanation


def model_factories() -> dict[str, Callable[[], object]]:
    return {
        "logreg": lambda: Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=400)),
            ]
        ),
        "knn": lambda: Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", KNeighborsClassifier(n_neighbors=21, weights="distance")),
            ]
        ),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=60,
            max_depth=12,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees": lambda: ExtraTreesClassifier(
            n_estimators=60,
            max_depth=None,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=-1,
        ),
    }
