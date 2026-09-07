from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
OFFICIAL_PAGE_BASE = "https://m.lottery.gov.cn"
OFFICIAL_API_BASE = "https://webapi.sporttery.cn"
HISTORY_ENDPOINT = f"{OFFICIAL_API_BASE}/gateway/lottery/getHistoryPageListV1.qry"
HISTORY_PAGE_SIZE = 30
INCREMENTAL_MAX_PAGES = 20

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
    existing = {
        record.issue: record
        for record in (existing_records or [])
        if record.lottery_type == lottery_type
    }
    fetched: dict[str, DrawRecord] = {}
    found_overlap = False
    page_no = 1
    total_pages = 1
    page_limit = max_pages
    if page_limit is None and existing:
        page_limit = INCREMENTAL_MAX_PAGES

    while page_no <= total_pages and (page_limit is None or page_no <= page_limit):
        page_payload = _fetch_json(
            HISTORY_ENDPOINT,
            params={
                "gameNo": config["game_no"],
                "provinceId": 0,
                "pageSize": HISTORY_PAGE_SIZE,
                "isVerify": 1,
                "pageNo": page_no,
            },
            referer=str(config["landing_page"]),
        )
        page_records = parse_history_payload(page_payload, lottery_type)
        if not page_records:
            raise ValueError(f"Official API returned no {lottery_type} records on page {page_no}")

        value = page_payload.get("value") or {}
        total_pages = max(1, int(value.get("pages") or 1))
        if any(record.issue in existing for record in page_records):
            found_overlap = True
        for record in page_records:
            fetched[record.issue] = record

        if existing and found_overlap:
            break
        page_no += 1

    if existing and not found_overlap:
        raise RuntimeError(
            f"Could not reconnect {lottery_type} history to the local dataset within "
            f"{page_limit or total_pages} pages; refusing to create a history gap"
        )

    merged = {**existing, **fetched}
    if not merged:
        raise ValueError(f"No records available for {lottery_type}")
    return sorted(merged.values(), key=lambda item: (item.draw_date, item.issue))


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
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch_json(url: str, params: dict[str, Any], referer: str) -> dict[str, Any]:
    last_error: Exception | None = None
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": referer,
        "Accept": "application/json, text/plain, */*",
    }
    for attempt in range(1, 5):
        try:
            request_url = f"{url}?{urlencode(params)}"
            request = Request(request_url, headers=headers)
            with urlopen(request, timeout=30) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except Exception as error:
            last_error = error
            if attempt == 4:
                break
            time.sleep(attempt * 0.8)
    assert last_error is not None
    raise last_error
