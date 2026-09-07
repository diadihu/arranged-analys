import pytest

from arranged_analys.data import sporttery
from arranged_analys.data.sporttery import DrawRecord, fetch_history, parse_draw_item, parse_history_payload


HISTORY_PAYLOAD_SAMPLE = {
    "errorCode": "0",
    "errorMessage": "处理成功",
    "value": {
        "pageNo": 1,
        "pages": 77,
        "total": 7629,
        "list": [
            {
                "lotteryGameName": "排列3",
                "lotteryGameNum": "35",
                "lotteryDrawNum": "26162",
                "lotteryDrawResult": "3 6 9",
                "lotteryDrawTime": "2026-06-21",
                "drawPdfUrl": "https://pdf.sporttery.cn/28200/26162/26162.pdf",
            }
        ],
    },
}


def test_parse_draw_item_extracts_official_fields() -> None:
    item = HISTORY_PAYLOAD_SAMPLE["value"]["list"][0]

    record = parse_draw_item(item, "p3")

    assert record.issue == "26162"
    assert record.draw_date == "2026-06-21"
    assert record.digits == [3, 6, 9]
    assert record.detail_url == "https://pdf.sporttery.cn/28200/26162/26162.pdf"


def test_parse_history_payload_reads_list() -> None:
    records = parse_history_payload(HISTORY_PAYLOAD_SAMPLE, "p3")

    assert len(records) == 1
    assert records[0].number == "369"


def _history_page(page_no: int, pages: int, issues: list[str]) -> dict:
    return {
        "errorCode": "0",
        "errorMessage": "处理成功",
        "value": {
            "pageNo": page_no,
            "pages": pages,
            "list": [
                {
                    "lotteryDrawNum": issue,
                    "lotteryDrawResult": "1 2 3",
                    "lotteryDrawTime": "2026-09-01",
                    "drawPdfUrl": f"https://example.com/{issue}.pdf",
                }
                for issue in issues
            ],
        },
    }


def test_fetch_history_reads_pages_until_existing_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        1: _history_page(1, 4, ["26203", "26202"]),
        2: _history_page(2, 4, ["26201"]),
        3: _history_page(3, 4, ["26200", "26199"]),
    }
    requested_pages: list[int] = []

    def fake_fetch_json(url: str, params: dict, referer: str) -> dict:
        requested_pages.append(params["pageNo"])
        return pages[params["pageNo"]]

    monkeypatch.setattr(sporttery, "_fetch_json", fake_fetch_json)
    existing = [
        DrawRecord("p3", "排列三", "26199", "2026-08-31", [9, 9, 9], "999", "")
    ]

    records = fetch_history("p3", existing_records=existing)

    assert requested_pages == [1, 2, 3]
    assert [record.issue for record in records] == ["26199", "26200", "26201", "26202", "26203"]
    assert records[0].number == "123"


def test_fetch_history_rejects_unconnected_increment(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_json(url: str, params: dict, referer: str) -> dict:
        return _history_page(params["pageNo"], 3, [f"2620{params['pageNo']}"])

    monkeypatch.setattr(sporttery, "_fetch_json", fake_fetch_json)
    existing = [
        DrawRecord("p3", "排列三", "26100", "2026-06-01", [9, 9, 9], "999", "")
    ]

    with pytest.raises(RuntimeError, match="refusing to create a history gap"):
        fetch_history("p3", max_pages=2, existing_records=existing)


def test_fetch_json_uses_configured_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_urls: list[str] = []

    class FakeHeaders:
        @staticmethod
        def get_content_charset() -> str:
            return "utf-8"

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        @staticmethod
        def read() -> bytes:
            return b'{"errorCode":"0","value":{"list":[]}}'

    def fake_urlopen(request, timeout: int):
        requested_urls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setenv("SPORTTERY_PROXY_URL", "https://example.vercel.app/api/sporttery")
    monkeypatch.setattr(sporttery, "urlopen", fake_urlopen)

    payload = sporttery._fetch_json(
        sporttery.HISTORY_ENDPOINT,
        params={"gameNo": "35", "pageNo": 7},
        referer="https://m.lottery.gov.cn/mkjpls/",
    )

    assert payload["errorCode"] == "0"
    assert requested_urls == [
        "https://example.vercel.app/api/sporttery?lotteryType=p3&pageNo=7"
    ]
