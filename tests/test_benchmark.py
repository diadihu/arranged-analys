from arranged_analys.data.sporttery import DrawRecord
from arranged_analys.models.benchmark import PositionProbability, build_rule_profile, rank_combinations


def _records() -> list[DrawRecord]:
    rows: list[DrawRecord] = []
    samples = [
        [1, 2, 3],
        [1, 2, 4],
        [1, 5, 4],
        [9, 5, 4],
        [9, 4, 5],
        [9, 4, 0],
    ]
    for index, digits in enumerate(samples, start=1):
        rows.append(
            DrawRecord(
                lottery_type="p3",
                display_name="排列三",
                issue=str(26000 + index),
                draw_date=f"2026-02-{index:02d}",
                digits=digits,
                number="".join(str(item) for item in digits),
                detail_url=f"https://example.com/{index}",
            )
        )
    return rows


def test_rank_combinations_returns_sorted_candidates() -> None:
    records = _records()
    rule_profile = build_rule_profile(records, digit_count=3)
    probabilities = [
        [
            PositionProbability(digit=9, probability=0.4),
            PositionProbability(digit=1, probability=0.3),
            PositionProbability(digit=0, probability=0.2),
        ],
        [
            PositionProbability(digit=4, probability=0.45),
            PositionProbability(digit=5, probability=0.25),
            PositionProbability(digit=2, probability=0.15),
        ],
        [
            PositionProbability(digit=5, probability=0.5),
            PositionProbability(digit=4, probability=0.2),
            PositionProbability(digit=0, probability=0.15),
        ],
    ]

    combinations = rank_combinations(records, "p3", probabilities, rule_profile)

    assert len(combinations) > 0
    assert combinations[0].combined_score >= combinations[-1].combined_score
