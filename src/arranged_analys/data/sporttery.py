from __future__ import annotations

import csv
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from curl_cffi import requests as curl_requests

USER_AGENT = "Mozilla/5.0"
OFFICIAL_PAGE_BASE = "https://m.lottery.gov.cn"
OFFICIAL_API_BASE = "https://webapi.sporttery.cn"
HISTORY_ENDPOINT = f"{OFFICIAL_API_BASE}/gateway/lottery/getHistoryPageListV1.qry"
SESSION_CACHE: dict[str, Any] = {}
HISTORY_PAGE_SIZE = 30

LOTTERY_CONFIG = {
    "p3": {
        "display_name": "排列三",
        "game_no": "35",
        "landing_page": f"{OFFICIAL_PAGE_BASE}/mkjpls/",
        "digit_count": 3,
    },
    "p5": {
        "display_name": "排列五",
        "game_no": "350133",
        "landing_page": f"{OFFICIAL_PAGE_BASE}/mkjplw/",
        "digit_count": 5,
    },
}


@dataclass(slots=True)
class DrawRecord:
    lottery_type: str
    display_name: str
    issue: str
    draw_date: str
    digits: list[int]
    number: str
    detail_url: str

    def to_row(self) -> dict[str, str]:
        row = {
            "draw_date": self.draw_date,
            "lottery_type": self.lottery_type,
            "issue": self.issue,
            "number": self.number,
            "detail_url": self.detail_url,
        }
        for index, digit in enumerate(self.digits, start=1):
            row[f"d{index}"] = str(digit)
        return row

    def to_dict(self) -> dict[str, str | list[int]]:
        return asdict(self)


def fetch_history(
    lottery_type: str,
    max_pages: int | None = None,
    existing_records: Iterable[DrawRecord] | None = None,
) -> list[DrawRecord]:
    if lottery_type not in LOTTERY_CONFIG:
        raise ValueError(f"Unsupported lottery_type: {lottery_type}")

    config = LOTTERY_CONFIG[lottery_type]
    first_page = _fetch_json(
        HISTORY_ENDPOINT,
        params={
            "gameNo": config["game_no"],
            "provinceId": 0,
            "pageSize": HISTORY_PAGE_SIZE,
            "isVerify": 1,
            "pageNo": 1,
        },
        referer=config["landing_page"],
    )
    records = parse_history_payload(first_page, lottery_type)
    if existing_records is not None:
        merged = {
            record.issue: record
            for record in existing_records
            if record.lottery_type == lottery_type
        }
        for record in records:
            merged[record.issue] = record
        return sorted(merged.values(), key=lambda item: (item.draw_date, item.issue))

    total_pages = int(first_page["value"]["pages"])
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    seen_issues = {record.issue for record in records}
    for page_no in range(2, total_pages + 1):
        try:
            page_payload = _fetch_json(
                HISTORY_ENDPOINT,
                params={
                    "gameNo": config["game_no"],
                    "provinceId": 0,
                    "pageSize": HISTORY_PAGE_SIZE,
                    "isVerify": 1,
                    "pageNo": page_no,
                },
                referer=config["landing_page"],
            )
        except Exception:
            break
        for record in parse_history_payload(page_payload, lottery_type):
            if record.issue in seen_issues:
                continue
            seen_issues.add(record.issue)
            records.append(record)

    return sorted(records, key=lambda item: (item.draw_date, item.issue))


def parse_history_payload(payload: dict[str, Any], lottery_type: str) -> list[DrawRecord]:
    if str(payload.get("errorCode")) != "0":
        raise ValueError(f"Official API returned error: {payload.get('errorMessage')}")
    value = payload.get("value") or {}
    items = value.get("list") or []
    return [parse_draw_item(item, lottery_type) for item in items]


def parse_draw_item(item: dict[str, Any], lottery_type: str) -> DrawRecord:
    config = LOTTERY_CONFIG[lottery_type]
    draw_result = str(item["lotteryDrawResult"]).strip()
    digits = [int(piece) for piece in draw_result.split() if piece != ""]
    if len(digits) != config["digit_count"]:
        raise ValueError(f"Unexpected digit count for {lottery_type}: {draw_result}")

    draw_time = str(item["lotteryDrawTime"]).strip()
    draw_date = draw_time[:10]
    detail_url = str(item.get("drawPdfUrl") or "").strip()
    return DrawRecord(
        lottery_type=lottery_type,
        display_name=str(config["display_name"]),
        issue=str(item["lotteryDrawNum"]).strip(),
        draw_date=draw_date,
        digits=digits,
        number="".join(str(digit) for digit in digits),
        detail_url=detail_url,
    )


def write_history_csv(records: Iterable[DrawRecord], file_path: str | Path) -> None:
    rows = [record.to_row() for record in records]
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["draw_date", "lottery_type", "issue", "number", "detail_url", "d1", "d2", "d3", "d4", "d5"]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(normalized_row)


def read_history_csv(file_path: str | Path) -> list[DrawRecord]:
    path = Path(file_path)
    if not path.exists():
        return []

    records: list[DrawRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            lottery_type = str(row["lottery_type"]).strip()
            config = LOTTERY_CONFIG.get(lottery_type)
            if not config:
                continue
            digit_count = int(config["digit_count"])
            digits = [int(row[f"d{index}"]) for index in range(1, digit_count + 1) if row.get(f"d{index}")]
            if len(digits) != digit_count:
                continue
            records.append(
                DrawRecord(
                    lottery_type=lottery_type,
                    display_name=str(config["display_name"]),
                    issue=str(row["issue"]).strip(),
                    draw_date=str(row["draw_date"]).strip(),
                    digits=digits,
                    number=str(row["number"]).strip(),
                    detail_url=str(row.get("detail_url", "")).strip(),
                )
            )
    return records


def updated_at_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _fetch_json(url: str, params: dict[str, Any], referer: str) -> dict[str, Any]:
    last_error: Exception | None = None
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": referer,
        "Accept": "application/json, text/plain, */*",
    }
    for attempt in range(1, 5):
        try:
            session = _get_or_create_session(referer, refresh=attempt > 1)
            response = session.get(
                url,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error
            if attempt == 4:
                break
            time.sleep(attempt * 0.8)
    assert last_error is not None
    raise last_error


def _get_or_create_session(referer: str, refresh: bool = False) -> Any:
    if refresh or referer not in SESSION_CACHE:
        session = curl_requests.Session(impersonate="chrome124")
        session.get(referer, headers={"User-Agent": USER_AGENT}, timeout=30)
        SESSION_CACHE[referer] = session
    return SESSION_CACHE[referer]
