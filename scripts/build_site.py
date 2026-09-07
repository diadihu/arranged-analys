from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arranged_analys.data.sporttery import (
    DrawRecord,
    HISTORY_ENDPOINT,
    fetch_history,
    read_history_csv,
    updated_at_iso,
    write_history_csv,
)
from arranged_analys.models.hybrid_prediction import build_advanced_prediction

DATA_RAW_DIR = ROOT / "data" / "raw"
DATA_PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DATA_DIR = ROOT / "docs" / "data"


def write_json(file_path: Path, payload: object) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


REQUIRED_SITE_OUTPUTS = (
    DATA_PROCESSED_DIR / "summary.json",
    DATA_PROCESSED_DIR / "predictions.json",
    DATA_PROCESSED_DIR / "benchmarks.json",
    DOCS_DATA_DIR / "summary.json",
    DOCS_DATA_DIR / "predictions.json",
    DOCS_DATA_DIR / "benchmarks.json",
    DOCS_DATA_DIR / "p3-history.json",
    DOCS_DATA_DIR / "p5-history.json",
)


def load_history_records(
    csv_path: Path,
    lottery_type: str,
    allow_stale: bool = False,
) -> tuple[list[DrawRecord], list[DrawRecord]]:
    existing_records = read_history_csv(csv_path)
    try:
        records = fetch_history(lottery_type, existing_records=existing_records)
    except Exception as error:
        if allow_stale and existing_records:
            print(
                f"[warn] failed to fetch latest {lottery_type} history, using cached csv instead: {error}",
                file=sys.stderr,
            )
            return existing_records, existing_records
        raise RuntimeError(f"Failed to fetch official {lottery_type} history") from error
    return existing_records, records


def history_changed(before: Sequence[DrawRecord], after: Sequence[DrawRecord]) -> bool:
    if len(before) != len(after):
        return True
    return any(old.to_row() != new.to_row() for old, new in zip(before, after))


def build_site_data(force_rebuild: bool = False, allow_stale: bool = False) -> bool:
    histories: dict[str, list[DrawRecord]] = {}
    new_record_counts: dict[str, int] = {}
    changed = False
    for lottery_type in ("p3", "p5"):
        csv_path = DATA_RAW_DIR / f"{lottery_type}_history.csv"
        previous_records, records = load_history_records(
            csv_path,
            lottery_type,
            allow_stale=allow_stale,
        )
        histories[lottery_type] = records
        new_record_counts[lottery_type] = max(0, len(records) - len(previous_records))
        changed = history_changed(previous_records, records) or changed
        print(
            f"[sync] {lottery_type}: {len(previous_records)} -> {len(records)} records, "
            f"latest={records[-1].issue} ({records[-1].draw_date})"
        )

    outputs_missing = any(not path.exists() for path in REQUIRED_SITE_OUTPUTS)
    if not changed and not force_rebuild and not outputs_missing:
        print("[sync] official API checked successfully; no new draw, skipping model rebuild")
        return False

    updated_at = updated_at_iso()
    all_predictions: dict[str, object] = {}
    all_benchmarks: dict[str, object] = {}
    summary_lotteries: dict[str, object] = {}

    for lottery_type in ("p3", "p5"):
        csv_path = DATA_RAW_DIR / f"{lottery_type}_history.csv"
        records = histories[lottery_type]
        prediction, benchmark_result = build_advanced_prediction(records, lottery_type=lottery_type)
        latest = records[-1]

        write_history_csv(records, csv_path)

        history_payload = {
            "lottery_type": lottery_type,
            "updated_at": updated_at,
            "records": [record.to_dict() for record in records],
        }
        write_json(DOCS_DATA_DIR / f"{lottery_type}-history.json", history_payload)

        summary_lotteries[lottery_type] = {
            "display_name": latest.display_name,
            "records_count": len(records),
            "latest_issue": latest.issue,
            "latest_draw_date": latest.draw_date,
            "latest_number": latest.number,
            "best_model_name": prediction.best_model_name,
            "best_feature_config": prediction.best_feature_config,
            "best_combo": prediction.best_combo["number"],
            "strategy_after_issue": prediction.latest_issue,
            "new_records": new_record_counts[lottery_type],
        }
        all_predictions[lottery_type] = prediction.to_dict()
        all_benchmarks[lottery_type] = benchmark_result.to_dict()

    summary_payload = {
        "updated_at": updated_at,
        "data_source": {
            "name": "中国体彩网官方高速 JSON 接口",
            "history_api": HISTORY_ENDPOINT,
            "latest_api": HISTORY_ENDPOINT,
            "latest_field": "value.lastPoolDraw / value.list[0]",
            "official_page": "https://m.lottery.gov.cn/mkjpls/",
        },
        "pipeline": {
            "status": "fresh",
            "generated_at": updated_at,
            "trigger": "history_change" if changed else "forced_rebuild",
        },
        "lotteries": summary_lotteries,
    }

    write_json(DATA_PROCESSED_DIR / "summary.json", summary_payload)
    write_json(DATA_PROCESSED_DIR / "predictions.json", all_predictions)
    write_json(DATA_PROCESSED_DIR / "benchmarks.json", all_benchmarks)
    write_json(DOCS_DATA_DIR / "summary.json", summary_payload)
    write_json(DOCS_DATA_DIR / "predictions.json", all_predictions)
    write_json(DOCS_DATA_DIR / "benchmarks.json", all_benchmarks)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh official lottery data and rebuild site outputs.")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild models even when no new draw exists.")
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="Allow cached CSV fallback for local diagnostics. Never use this option in CI.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    build_site_data(force_rebuild=arguments.force_rebuild, allow_stale=arguments.allow_stale)
