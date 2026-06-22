from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
import csv
import math
import re
import time
from typing import Iterable
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0"
BASE_URL = "https://www.js-lottery.com"
PAGE_ENDPOINT = f"{BASE_URL}/Lottery/_ListData"

LOTTERY_CONFIG = {
    "p3": {
        "display_name": "排列三",
        "landing_page": f"{BASE_URL}/wfzq/p3p5/p3data",
        "digit_count": 3,
    },
    "p5": {
        "display_name": "排列五",
        "landing_page": f"{BASE_URL}/wfzq/p3p5/p5data",
        "digit_count": 5,
    },
}

TABLE_ROW_RE = re.compile(r"<tr[^>]*>(?P<row>.*?)</tr>", re.IGNORECASE | re.DOTALL)
TABLE_CELL_RE = re.compile(r"<td[^>]*>(?P<cell>.*?)</td>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r"href=\"(?P<href>[^\"]+)\"", re.IGNORECASE)
PAGE_META_RE = re.compile(
    r"data-pageindex=\"(?P<page_index>\d+)\"[^>]*data-size=\"(?P<page_size>\d+)\"[^>]*data-sum=\"(?P<total>\d+)\"",
    re.IGNORECASE,
)


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


def _fetch_text(url: str, params: dict[str, str | int] | None = None) -> str:
    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params)}"
    last_error: Exception | None = None
    for attempt in range(1, 5):
        request = Request(full_url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="ignore")
        except URLError as error:
            last_error = error
            if attempt == 4:
                break
            time.sleep(attempt * 0.8)
    assert last_error is not None
    raise last_error


def _clean_fragment(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_history_rows(html: str, lottery_type: str) -> list[DrawRecord]:
    config = LOTTERY_CONFIG[lottery_type]
    digit_count = config["digit_count"]
    rows: list[DrawRecord] = []
    for row_match in TABLE_ROW_RE.finditer(html):
        row_html = row_match.group("row")
        cells = TABLE_CELL_RE.findall(row_html)
        if len(cells) < 4:
            continue
        draw_date = _clean_fragment(cells[0])
        issue = _clean_fragment(cells[1])
        number_text = _clean_fragment(cells[2])
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", draw_date):
            continue
        if not re.fullmatch(r"\d+", issue):
            continue
        digits = [int(item) for item in re.findall(r"\d", number_text)]
        if len(digits) != digit_count:
            continue
        href_match = HREF_RE.search(cells[3])
        if not href_match:
            continue
        detail_url = href_match.group("href").strip()
        if detail_url.startswith("/"):
            detail_url = f"{BASE_URL}{detail_url}"
        rows.append(
            DrawRecord(
                lottery_type=lottery_type,
                display_name=config["display_name"],
                issue=issue,
                draw_date=draw_date,
                digits=digits,
                number="".join(str(digit) for digit in digits),
                detail_url=detail_url,
            )
        )
    return rows


def parse_total_pages(html: str) -> int:
    match = PAGE_META_RE.search(html)
    if not match:
        return 1
    page_size = int(match.group("page_size"))
    total = int(match.group("total"))
    return max(1, math.ceil(total / page_size))


def fetch_history(lottery_type: str, max_pages: int | None = None, delay_seconds: float = 0.0) -> list[DrawRecord]:
    if lottery_type not in LOTTERY_CONFIG:
        raise ValueError(f"Unsupported lottery_type: {lottery_type}")

    first_page_html = _fetch_text(PAGE_ENDPOINT, {"itemType": lottery_type})
    records = parse_history_rows(first_page_html, lottery_type)
    total_pages = parse_total_pages(first_page_html)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    seen_issues = {record.issue for record in records}
    for page_index in range(2, total_pages + 1):
        page_html = _fetch_text(PAGE_ENDPOINT, {"itemType": lottery_type, "pageIndex": page_index})
        for record in parse_history_rows(page_html, lottery_type):
            if record.issue in seen_issues:
                continue
            seen_issues.add(record.issue)
            records.append(record)
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return sorted(records, key=lambda item: (item.draw_date, item.issue))


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


def updated_at_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
