from arranged_analys.data.sporttery import parse_draw_item, parse_history_payload


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
