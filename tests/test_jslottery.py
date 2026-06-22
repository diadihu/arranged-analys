from arranged_analys.data.jslottery import parse_history_rows, parse_total_pages


HTML_SAMPLE = """
<table>
  <tr>
    <td style="text-align:center;">2026-06-21</td>
    <td style="text-align:center;">26162</td>
    <td style="text-align:center;">3 6 9</td>
    <td style="text-align:center;"><a href="/cms/post-147291.html">详细</a></td>
  </tr>
  <tr>
    <td style="text-align:center;">2026-06-20</td>
    <td style="text-align:center;">26161</td>
    <td style="text-align:center;">5 6 2</td>
    <td style="text-align:center;"><a href="/cms/post-147286.html">详细</a></td>
  </tr>
</table>
<div data-ajaxloadurl="/Lottery/_ListData?itemType=p3" data-mode="NumericNextPrevious" data-pageindex="1" data-plugin="page" data-size="10" data-sum="7629" data-targetid="_ListData"></div>
"""


def test_parse_history_rows_extracts_records() -> None:
    rows = parse_history_rows(HTML_SAMPLE, "p3")

    assert len(rows) == 2
    assert rows[0].issue == "26162"
    assert rows[0].digits == [3, 6, 9]
    assert rows[0].detail_url == "https://www.js-lottery.com/cms/post-147291.html"


def test_parse_total_pages_reads_pagination_metadata() -> None:
    total_pages = parse_total_pages(HTML_SAMPLE)

    assert total_pages == 763
