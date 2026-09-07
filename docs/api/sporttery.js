import { request as httpsRequest } from "node:https";

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
const OFFICIAL_HOST = "webapi.sporttery.cn";
const DNS_ENDPOINT =
  "https://dns.google/resolve?name=webapi.sporttery.cn&type=A";

let cachedAddress = null;
let addressExpiresAt = 0;

async function resolveOfficialAddress() {
  if (cachedAddress && Date.now() < addressExpiresAt) {
    return cachedAddress;
  }

  const dnsResponse = await fetch(DNS_ENDPOINT, {
    headers: { Accept: "application/dns-json" },
    signal: AbortSignal.timeout(8000),
  });
  if (!dnsResponse.ok) {
    throw new Error(`DNS lookup failed with ${dnsResponse.status}`);
  }

  const dnsPayload = await dnsResponse.json();
  const address = dnsPayload.Answer?.find(
    (answer) => answer.type === 1 && /^\d{1,3}(?:\.\d{1,3}){3}$/.test(answer.data),
  )?.data;
  if (!address) {
    throw new Error("DNS lookup returned no IPv4 address");
  }

  cachedAddress = address;
  addressExpiresAt = Date.now() + 5 * 60 * 1000;
  return address;
}

function requestOfficialPayload(upstreamUrl, address, headers) {
  return new Promise((resolve, reject) => {
    const request = httpsRequest(
      {
        protocol: "https:",
        hostname: address,
        servername: OFFICIAL_HOST,
        method: "GET",
        path: `${upstreamUrl.pathname}${upstreamUrl.search}`,
        headers: {
          ...headers,
          Host: OFFICIAL_HOST,
        },
        timeout: 25000,
      },
      (upstreamResponse) => {
        const chunks = [];
        let size = 0;

        upstreamResponse.on("data", (chunk) => {
          size += chunk.length;
          if (size > 2 * 1024 * 1024) {
            request.destroy(new Error("Official API response is too large"));
            return;
          }
          chunks.push(chunk);
        });
        upstreamResponse.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          const status = upstreamResponse.statusCode || 502;
          if (status < 200 || status >= 300) {
            reject(new Error(`Official API returned HTTP ${status}`));
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch {
            reject(new Error("Official API returned invalid JSON"));
          }
        });
      },
    );

    request.on("timeout", () => request.destroy(new Error("Official API timed out")));
    request.on("error", reject);
    request.end();
  });
}

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
    const headers = {
      Accept: "application/json, text/plain, */*",
      Referer: config.referer,
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    };
    const address = await resolveOfficialAddress();
    const payload = await requestOfficialPayload(upstreamUrl, address, headers);
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
