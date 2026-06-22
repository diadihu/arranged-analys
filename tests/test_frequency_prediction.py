from arranged_analys.data.jslottery import DrawRecord
from arranged_analys.models.frequency_prediction import build_frequency_prediction


def test_build_frequency_prediction_returns_primary_prediction() -> None:
    records = [
        DrawRecord("p3", "排列三", "26160", "2026-06-19", [1, 2, 3], "123", "https://example.com/1"),
        DrawRecord("p3", "排列三", "26161", "2026-06-20", [1, 2, 4], "124", "https://example.com/2"),
        DrawRecord("p3", "排列三", "26162", "2026-06-21", [1, 5, 4], "154", "https://example.com/3"),
    ]

    prediction = build_frequency_prediction(records, "p3", window_size=3)

    assert prediction.primary_prediction == "124"
    assert prediction.recommended_combinations[0].number == "124"
