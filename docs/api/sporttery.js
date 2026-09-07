const LOTTERIES = {
  p3: {
    gameNo: "35",
    referer: "https://m.lottery.gov.cn/mkjpls/",
  },
  p5: {
    gameNo: "350133",
    referer: "https://m.lottery.gov.cn/mkjplw/",
  },
};

const HISTORY_ENDPOINT =
  "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry";

export default async function handler(request, response) {
  if (request.method !== "GET") {
    response.setHeader("Allow", "GET");
    return response.status(405).json({ error: "Method not allowed" });
  }

  const lotteryType = String(request.query.lotteryType || "");
  const pageNo = Number.parseInt(String(request.query.pageNo || "1"), 10);
  const config = LOTTERIES[lotteryType];
  if (!config || !Number.isInteger(pageNo) || pageNo < 1 || pageNo > 400) {
    return response.status(400).json({ error: "Invalid lotteryType or pageNo" });
  }

  const upstreamUrl = new URL(HISTORY_ENDPOINT);
  upstreamUrl.searchParams.set("gameNo", config.gameNo);
  upstreamUrl.searchParams.set("provinceId", "0");
  upstreamUrl.searchParams.set("pageSize", "30");
  upstreamUrl.searchParams.set("isVerify", "1");
  upstreamUrl.searchParams.set("pageNo", String(pageNo));

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      headers: {
        Accept: "application/json, text/plain, */*",
        Referer: config.referer,
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      },
      signal: AbortSignal.timeout(25000),
    });
    if (!upstreamResponse.ok) {
      return response.status(502).json({
        error: "Official API request failed",
        upstreamStatus: upstreamResponse.status,
      });
    }

    const payload = await upstreamResponse.json();
    if (String(payload.errorCode) !== "0") {
      return response.status(502).json({
        error: "Official API returned an error",
        upstreamCode: payload.errorCode,
      });
    }

    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader("Cache-Control", "public, s-maxage=30, stale-while-revalidate=120");
    return response.status(200).json(payload);
  } catch (error) {
    return response.status(502).json({
      error: "Official API request failed",
      detail: error instanceof Error ? error.message : "Unknown error",
    });
  }
}
