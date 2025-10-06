from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

from .http import HttpClient


@dataclass
class EnrichedMetrics:
    keyword: str
    naver_blog_total: Optional[int] = None
    google_total: Optional[int] = None
    naver_monthly_pc: Optional[int] = None
    naver_monthly_mobile: Optional[int] = None
    naver_cpc: Optional[float] = None


class NaverOpenApiEnricher:
    """Fetch blog search totals from Naver OpenAPI.

    Requires env:
      - NAVER_OPENAPI_CLIENT_ID
      - NAVER_OPENAPI_CLIENT_SECRET
    """

    BASE_URL = "https://openapi.naver.com/v1/search/blog.json"

    def __init__(self, client_id: str, client_secret: str, http: HttpClient | None = None) -> None:
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        self.http = http or HttpClient(headers=headers)

    def blog_total(self, keyword: str) -> Optional[int]:
        try:
            data = self.http.get_json(self.BASE_URL, params={"query": keyword, "display": 1})
            total = data.get("total") if isinstance(data, dict) else None
            if isinstance(total, int):
                return total
        except Exception:
            return None
        return None


class GoogleCSEnricher:
    """Fetch total results from Google Custom Search.

    Requires env:
      - GOOGLE_API_KEY
      - GOOGLE_CSE_CX
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cx: str, http: HttpClient | None = None) -> None:
        self.api_key = api_key
        self.cx = cx
        self.http = http or HttpClient()

    def total_results(self, keyword: str) -> Optional[int]:
        try:
            data = self.http.get_json(self.BASE_URL, params={"key": self.api_key, "cx": self.cx, "q": keyword})
            info = data.get("searchInformation") if isinstance(data, dict) else None
            total = info.get("totalResults") if isinstance(info, dict) else None
            if isinstance(total, str) and total.isdigit():
                return int(total)
        except Exception:
            return None
        return None


class NaverAdsEnricher:
    """Fetch monthly volume and CPC-like metric from Naver SearchAd API Keyword Tool.

    Requires env:
      - NAVER_AD_CUSTOMER_ID
      - NAVER_AD_API_KEY
      - NAVER_AD_SECRET_KEY
    Docs: https://api.searchad.naver.com
    Endpoint: GET /keywordstool?hintKeywords=...&showDetail=1
    """

    BASE_URL = "https://api.searchad.naver.com"

    def __init__(self, customer_id: str, api_key: str, secret_key: str, http: HttpClient | None = None) -> None:
        self.customer_id = customer_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.http = http or HttpClient()

    def _signature(self, timestamp: str, method: str, path: str) -> str:
        msg = f"{timestamp}.{method}.{path}"
        digest = hmac.new(self.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _headers(self, method: str, path: str) -> Dict[str, str]:
        ts = str(int(time.time() * 1000))
        return {
            "X-Timestamp": ts,
            "X-API-KEY": self.api_key,
            "X-Customer": self.customer_id,
            "X-Signature": self._signature(ts, method, path),
        }

    def keyword_stats(self, keyword: str) -> tuple[Optional[int], Optional[int], Optional[float]]:
        path = "/keywordstool"
        url = f"{self.BASE_URL}{path}"
        headers = self._headers("GET", path)
        try:
            # Use our HttpClient but override headers per request
            client = HttpClient(headers=headers)
            data = client.get_json(url, params={"hintKeywords": keyword, "showDetail": 1})
            # data: { keywordList: [ { monthlyPcQcCnt, monthlyMobileQcCnt, relKeyword, ... , plAvgCpc? } ] }
            lst = data.get("keywordList") if isinstance(data, dict) else None
            if isinstance(lst, list) and lst:
                it = lst[0]
                pc = it.get("monthlyPcQcCnt") if isinstance(it, dict) else None
                mob = it.get("monthlyMobileQcCnt") if isinstance(it, dict) else None
                # Some fields expose cpc as 'plAvgCpc' or 'avgPcBid' etc., vary by account
                cpc_raw = None
                for key in ("plAvgCpc", "avgPcBid", "avgMobileBid"):
                    if isinstance(it, dict) and key in it:
                        cpc_raw = it.get(key)
                        break
                pc_i = int(pc) if isinstance(pc, (int, float, str)) and str(pc).isdigit() else None
                mob_i = int(mob) if isinstance(mob, (int, float, str)) and str(mob).isdigit() else None
                cpc_f = float(cpc_raw) if isinstance(cpc_raw, (int, float)) else None
                return pc_i, mob_i, cpc_f
        except Exception:
            return None, None, None
        return None, None, None


def build_enrichers_from_env() -> Dict[str, object]:
    enrichers: Dict[str, object] = {}
    naver_cid = os.getenv("NAVER_AD_CUSTOMER_ID")
    naver_key = os.getenv("NAVER_AD_API_KEY")
    naver_secret = os.getenv("NAVER_AD_SECRET_KEY")
    if naver_cid and naver_key and naver_secret:
        enrichers["naver_ads"] = NaverAdsEnricher(naver_cid, naver_key, naver_secret)

    open_id = os.getenv("NAVER_OPENAPI_CLIENT_ID")
    open_secret = os.getenv("NAVER_OPENAPI_CLIENT_SECRET")
    if open_id and open_secret:
        enrichers["naver_openapi"] = NaverOpenApiEnricher(open_id, open_secret)

    g_key = os.getenv("GOOGLE_API_KEY")
    g_cx = os.getenv("GOOGLE_CSE_CX")
    if g_key and g_cx:
        enrichers["google_cse"] = GoogleCSEnricher(g_key, g_cx)
    return enrichers


def enrich_keywords(keywords: list[str], enrichers: Dict[str, object], limit: int | None = None) -> Dict[str, EnrichedMetrics]:
    out: Dict[str, EnrichedMetrics] = {}
    limit = limit or len(keywords)
    for kw in keywords[:limit]:
        m = EnrichedMetrics(keyword=kw)
        if "naver_openapi" in enrichers:
            m.naver_blog_total = enrichers["naver_openapi"].blog_total(kw)  # type: ignore[attr-defined]
        if "google_cse" in enrichers:
            m.google_total = enrichers["google_cse"].total_results(kw)  # type: ignore[attr-defined]
        if "naver_ads" in enrichers:
            pc, mob, cpc = enrichers["naver_ads"].keyword_stats(kw)  # type: ignore[attr-defined]
            m.naver_monthly_pc, m.naver_monthly_mobile, m.naver_cpc = pc, mob, cpc
        out[kw] = m
    return out

