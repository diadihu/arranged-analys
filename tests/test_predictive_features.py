from arranged_analys.data.sporttery import DrawRecord
from arranged_analys.features.predictive import FeatureConfig, build_next_feature_row, build_supervised_dataset


def _build_records() -> list[DrawRecord]:
    records: list[DrawRecord] = []
    for index in range(1, 40):
        digits = [index % 10, (index + 1) % 10, (index + 2) % 10]
        records.append(
            DrawRecord(
                lottery_type="p3",
                display_name="排列三",
                issue=str(26000 + index),
                draw_date=f"2026-01-{index:02d}",
                digits=digits,
                number="".join(str(item) for item in digits),
                detail_url=f"https://example.com/{index}",
            )
        )
    return records


def test_build_supervised_dataset_creates_rows() -> None:
    records = _build_records()
    config = FeatureConfig(name="test", lag_depth=4, rolling_windows=(5, 10))

    dataset = build_supervised_dataset(records, "p3", config)

    assert dataset.X.shape[0] == len(records) - 10
    assert dataset.y.shape[1] == 3
    assert len(dataset.feature_names) == dataset.X.shape[1]


def test_build_next_feature_row_matches_feature_width() -> None:
    records = _build_records()
    config = FeatureConfig(name="test", lag_depth=4, rolling_windows=(5, 10))
    dataset = build_supervised_dataset(records, "p3", config)

    next_row, feature_names = build_next_feature_row(records, "p3", config)

    assert next_row.shape[0] == dataset.X.shape[1]
    assert len(feature_names) == dataset.X.shape[1]
