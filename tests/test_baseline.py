import pandas as pd

from arranged_analys.features.engineering import build_basic_features
from arranged_analys.models.baseline import predict_by_recent_frequency


def test_predict_by_recent_frequency_returns_top_digit_per_position() -> None:
    df = pd.DataFrame(
        {
            "draw_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "lottery_type": ["p3", "p3", "p3"],
            "issue": ["1", "2", "3"],
            "d1": [1, 1, 2],
            "d2": [3, 3, 4],
            "d3": [5, 5, 6],
        }
    )

    features = build_basic_features(df, digit_count=3)
    result = predict_by_recent_frequency(features, lottery_type="p3", digit_count=3, window_size=3)

    assert result.predicted_digits == [1, 3, 5]
