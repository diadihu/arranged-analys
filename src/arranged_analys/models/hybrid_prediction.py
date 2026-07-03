from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from arranged_analys.data.sporttery import DrawRecord, LOTTERY_CONFIG
from arranged_analys.models.benchmark import BenchmarkSelectionResult, run_benchmark_selection
from arranged_analys.models.frequency_prediction import build_frequency_prediction


@dataclass(slots=True)
class AdvancedPredictionResult:
    lottery_type: str
    display_name: str
    latest_issue: str
    latest_number: str
    baseline_prediction: str
    best_model_name: str
    best_feature_config: str
    holdout_size: int
    best_combo: dict[str, object]
    holdout_metrics: dict[str, float]
    combo_backtest: dict[str, float | int]
    combination_profile: dict[str, object]
    positional_candidates: list[list[dict[str, float | int]]]
    recommended_combinations: list[dict[str, object]]
    rule_profile: dict[str, list[int]]
    benchmark_table: list[dict[str, object]]
    disclaimer: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_advanced_prediction(
    records: Sequence[DrawRecord],
    lottery_type: str,
) -> tuple[AdvancedPredictionResult, BenchmarkSelectionResult]:
    config = LOTTERY_CONFIG[lottery_type]
    latest = records[-1]
    baseline = build_frequency_prediction(records, lottery_type=lottery_type)
    benchmark_result = run_benchmark_selection(records, lottery_type=lottery_type)

    best_combo = benchmark_result.ranked_combinations[0]
    positional_candidates = [
        [candidate.to_dict() for candidate in position_items[:4]]
        for position_items in benchmark_result.position_probabilities
    ]
    result = AdvancedPredictionResult(
        lottery_type=lottery_type,
        display_name=str(config["display_name"]),
        latest_issue=latest.issue,
        latest_number=latest.number,
        baseline_prediction=baseline.primary_prediction,
        best_model_name=benchmark_result.best_model_name,
        best_feature_config=benchmark_result.feature_config.name,
        holdout_size=benchmark_result.holdout_size,
        best_combo=best_combo.to_dict(),
        holdout_metrics=benchmark_result.best_metrics.to_dict(),
        combo_backtest=benchmark_result.combo_backtest.to_dict(),
        combination_profile=benchmark_result.combination_profile.to_dict(),
        positional_candidates=positional_candidates,
        recommended_combinations=[item.to_dict() for item in benchmark_result.ranked_combinations],
        rule_profile=benchmark_result.rule_profile.to_dict(),
        benchmark_table=[item.to_dict() for item in benchmark_result.benchmarks],
        disclaimer="结果基于历史开奖统计、时序交叉验证、位置级回测与组合级回放，仅作数据实验参考。",
    )
    return result, benchmark_result
