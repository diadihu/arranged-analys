from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import product
from typing import Iterable

from arranged_analys.data.jslottery import DrawRecord, LOTTERY_CONFIG


@dataclass(slots=True)
class PositionCandidate:
    digit: int
    count: int
    ratio: float


@dataclass(slots=True)
class RecommendedCombination:
    number: str
    score: float


@dataclass(slots=True)
class PredictionResult:
    lottery_type: str
    display_name: str
    window_size: int
    latest_issue: str
    latest_number: str
    primary_prediction: str
    positional_candidates: list[list[PositionCandidate]]
    recommended_combinations: list[RecommendedCombination]
    disclaimer: str

    def to_dict(self) -> dict[str, object]:
        return {
            "lottery_type": self.lottery_type,
            "display_name": self.display_name,
            "window_size": self.window_size,
            "latest_issue": self.latest_issue,
            "latest_number": self.latest_number,
            "primary_prediction": self.primary_prediction,
            "positional_candidates": [
                [asdict(candidate) for candidate in candidates]
                for candidates in self.positional_candidates
            ],
            "recommended_combinations": [
                asdict(combination) for combination in self.recommended_combinations
            ],
            "disclaimer": self.disclaimer,
        }


def build_frequency_prediction(
    records: Iterable[DrawRecord],
    lottery_type: str,
    window_size: int = 120,
) -> PredictionResult:
    config = LOTTERY_CONFIG[lottery_type]
    digit_count = config["digit_count"]
    history = list(records)
    if not history:
        raise ValueError(f"No records available for {lottery_type}")

    recent_records = history[-window_size:]
    primary_digits: list[str] = []
    positional_candidates: list[list[PositionCandidate]] = []

    for position in range(digit_count):
        counter = Counter(record.digits[position] for record in recent_records)
        total = sum(counter.values())
        ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        top_candidates = [
            PositionCandidate(
                digit=digit,
                count=count,
                ratio=round(count / total, 4),
            )
            for digit, count in ordered[:3]
        ]
        positional_candidates.append(top_candidates)
        primary_digits.append(str(top_candidates[0].digit))

    recommended_combinations = _build_recommended_combinations(positional_candidates, lottery_type)
    latest = history[-1]
    return PredictionResult(
        lottery_type=lottery_type,
        display_name=config["display_name"],
        window_size=len(recent_records),
        latest_issue=latest.issue,
        latest_number=latest.number,
        primary_prediction="".join(primary_digits),
        positional_candidates=positional_candidates,
        recommended_combinations=recommended_combinations,
        disclaimer="仅基于近期位频统计生成实验性结果，不构成任何投注建议。",
    )


def _build_recommended_combinations(
    positional_candidates: list[list[PositionCandidate]],
    lottery_type: str,
) -> list[RecommendedCombination]:
    per_position_limit = 3 if lottery_type == "p3" else 2
    limited_candidates = [candidates[:per_position_limit] for candidates in positional_candidates]
    combinations: list[RecommendedCombination] = []
    for candidate_group in product(*limited_candidates):
        number = "".join(str(candidate.digit) for candidate in candidate_group)
        score = 1.0
        for candidate in candidate_group:
            score *= candidate.ratio
        combinations.append(RecommendedCombination(number=number, score=round(score, 6)))
    combinations.sort(key=lambda item: (-item.score, item.number))
    return combinations[:10]
