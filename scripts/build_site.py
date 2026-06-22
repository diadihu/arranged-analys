from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arranged_analys.data.sporttery import fetch_history, read_history_csv, updated_at_iso, write_history_csv
from arranged_analys.models.frequency_prediction import build_frequency_prediction

DATA_RAW_DIR = ROOT / "data" / "raw"
DATA_PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DATA_DIR = ROOT / "docs" / "data"


def write_json(file_path: Path, payload: object) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_site_data() -> None:
    updated_at = updated_at_iso()
    all_predictions: dict[str, object] = {}
    summary_lotteries: dict[str, object] = {}

    for lottery_type in ("p3", "p5"):
        csv_path = DATA_RAW_DIR / f"{lottery_type}_history.csv"
        existing_records = read_history_csv(csv_path)
        records = fetch_history(lottery_type, existing_records=existing_records)
        prediction = build_frequency_prediction(records, lottery_type=lottery_type)
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
        }
        all_predictions[lottery_type] = prediction.to_dict()

    summary_payload = {
        "updated_at": updated_at,
        "data_source": {
            "name": "中国体彩网官方 JSON 接口",
            "history_api": "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry",
            "latest_api": "https://webapi.sporttery.cn/gateway/lottery/getDigitalDrawInfoV1.qry",
            "official_page": "https://m.lottery.gov.cn/mkjpls/",
        },
        "lotteries": summary_lotteries,
    }

    write_json(DATA_PROCESSED_DIR / "summary.json", summary_payload)
    write_json(DATA_PROCESSED_DIR / "predictions.json", all_predictions)
    write_json(DOCS_DATA_DIR / "summary.json", summary_payload)
    write_json(DOCS_DATA_DIR / "predictions.json", all_predictions)


if __name__ == "__main__":
    build_site_data()
