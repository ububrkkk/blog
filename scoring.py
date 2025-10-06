from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List

from .text_utils import tokenize


COMMERCIAL_MODIFIERS = {
    "가격": 1.2,
    "할인": 1.4,
    "쿠폰": 1.3,
    "구매": 1.1,
    "추천": 1.15,
    "비교": 1.1,
}

INFORMATIONAL_MODIFIERS = {
    "방법": 1.2,
    "가이드": 1.15,
    "설정": 1.1,
    "문제": 1.05,
    "고장": 1.1,
    "후기": 1.1,
    "리뷰": 1.1,
}


def _length_score(tokens: List[str]) -> float:
    # Favor 2~5 tokens as practical long-tail range
    n = len(tokens)
    if n <= 1:
        return 0.3
    if 2 <= n <= 5:
        return 1.0
    if 6 <= n <= 8:
        return 0.8
    return 0.6


def _modifier_boost(tokens: List[str]) -> float:
    boost = 1.0
    for t in tokens:
        boost *= COMMERCIAL_MODIFIERS.get(t, 1.0)
        boost *= INFORMATIONAL_MODIFIERS.get(t, 1.0)
    return min(boost, 2.2)


def estimate_demand_score(q: str, provider_hits: int = 1) -> float:
    """Estimate demand based on structure and provider frequency.

    provider_hits: how many providers/seeds surfaced this query.
    """
    tokens = tokenize(q)
    base = _length_score(tokens)
    base *= _modifier_boost(tokens)
    # Provider hit frequency as soft signal
    base *= 1.0 + min(provider_hits, 5) * 0.1
    return min(base, 3.0)


def estimate_competition_score(q: str) -> float:
    """Very rough competition proxy using head-term bias and modifiers.

    Lower is better (easier). Returns 0.5~2.5 range approximately.
    """
    tokens = tokenize(q)
    if len(tokens) <= 1:
        return 2.2  # likely a head term
    score = 1.4
    # Longer tails slightly easier
    score -= min(max(len(tokens) - 2, 0) * 0.12, 0.6)
    # Informational modifiers ease competition; commercial increase it
    for t in tokens:
        if t in INFORMATIONAL_MODIFIERS:
            score -= 0.08
        if t in COMMERCIAL_MODIFIERS:
            score += 0.06
    return max(0.5, min(score, 2.5))


@dataclass
class KeywordScore:
    keyword: str
    demand: float
    competition: float
    opportunity: float
    provider_hits: int


def score_keywords(keywords: Iterable[str], hit_counts: Dict[str, int] | None = None) -> List[KeywordScore]:
    results: List[KeywordScore] = []
    hit_counts = hit_counts or {}
    for kw in keywords:
        hits = hit_counts.get(kw, 1)
        d = estimate_demand_score(kw, provider_hits=hits)
        c = estimate_competition_score(kw)
        opp = max(d * 1.4 - c, 0.0)
        results.append(KeywordScore(keyword=kw, demand=round(d, 3), competition=round(c, 3), opportunity=round(opp, 3), provider_hits=hits))
    # Sort by opportunity desc, then demand desc
    results.sort(key=lambda x: (x.opportunity, x.demand), reverse=True)
    return results


def _comp_from_results(total: int) -> float:
    # Convert total result count to a 0.6 ~ 2.3 competition estimate
    if total <= 0:
        return 0.8
    return max(0.6, min(2.3, 0.7 + (math.log10(total + 1) * 0.25)))


def score_keywords_with_metrics(
    keywords: Iterable[str],
    hit_counts: Dict[str, int] | None,
    metrics: Dict[str, object],
) -> List[KeywordScore]:
    """Score with optional real metrics.

    metrics is a mapping from keyword to an object that may expose attributes:
      - naver_monthly_pc, naver_monthly_mobile, naver_cpc
      - naver_blog_total, google_total
    Falls back to heuristic where data is missing.
    """
    hit_counts = hit_counts or {}
    results: List[KeywordScore] = []
    for kw in keywords:
        hits = hit_counts.get(kw, 1)
        base_demand = estimate_demand_score(kw, provider_hits=hits)
        base_comp = estimate_competition_score(kw)

        m = metrics.get(kw)
        d = base_demand
        c = base_comp
        if m is not None:
            # Demand by monthly volumes
            try:
                monthly_pc = getattr(m, "naver_monthly_pc", None)
                monthly_mob = getattr(m, "naver_monthly_mobile", None)
                cpc = getattr(m, "naver_cpc", None)
                monthly_sum = (monthly_pc or 0) + (monthly_mob or 0)
                if monthly_sum > 0:
                    # Log scale volume to 0.6~3.0
                    d = min(3.0, 0.6 + math.log10(1 + monthly_sum) * 0.6 + min(hits, 5) * 0.05)
                    if isinstance(cpc, (int, float)) and cpc > 0:
                        # Small boost for higher CPC
                        d = min(3.0, d + min(cpc / 5000.0, 0.3))
            except Exception:
                pass

            # Competition by results count
            try:
                nav_tot = getattr(m, "naver_blog_total", None)
                g_tot = getattr(m, "google_total", None)
                comps = []
                if isinstance(nav_tot, int):
                    comps.append(_comp_from_results(nav_tot))
                if isinstance(g_tot, int):
                    comps.append(_comp_from_results(g_tot))
                if comps:
                    # average, keep within 0.5~2.5
                    c = max(0.5, min(sum(comps) / len(comps), 2.5))
            except Exception:
                pass

        opp = max(d * 1.4 - c, 0.0)
        results.append(KeywordScore(keyword=kw, demand=round(d, 3), competition=round(c, 3), opportunity=round(opp, 3), provider_hits=hits))

    results.sort(key=lambda x: (x.opportunity, x.demand), reverse=True)
    return results


def score_keywords_by_platform(
    keywords: Iterable[str],
    hit_counts: Dict[str, int] | None,
    metrics: Dict[str, object] | None,
    platform: str = "naver",
) -> List[KeywordScore]:
    """Platform-aware scoring.

    - naver: competition 우선 Naver 블로그 문서 수, 수요는 네이버 월간 볼륨 비중↑
    - tistory: 경쟁도는 Google 결과 수 비중↑, 수요는 롱테일/정보성 비중 및 볼륨 소폭 반영
    """
    platform = platform.lower()
    hit_counts = hit_counts or {}
    metrics = metrics or {}
    results: List[KeywordScore] = []

    for kw in keywords:
        hits = hit_counts.get(kw, 1)
        # base heuristic
        d = estimate_demand_score(kw, provider_hits=hits)
        c = estimate_competition_score(kw)

        m = metrics.get(kw)
        if platform == "naver":
            # Demand: strong effect of monthly volume + CPC
            try:
                monthly_sum = ((getattr(m, "naver_monthly_pc", 0) or 0) + (getattr(m, "naver_monthly_mobile", 0) or 0)) if m else 0
                cpc = getattr(m, "naver_cpc", None) if m else None
                if monthly_sum > 0:
                    d = min(3.0, 0.7 + math.log10(1 + monthly_sum) * 0.7 + min(hits, 5) * 0.05)
                    if isinstance(cpc, (int, float)) and cpc > 0:
                        d = min(3.0, d + min(cpc / 4000.0, 0.35))
            except Exception:
                pass
            # Competition: prioritize Naver blog total
            try:
                nav_tot = getattr(m, "naver_blog_total", None) if m else None
                if isinstance(nav_tot, int):
                    c = max(0.5, min(_comp_from_results(nav_tot), 2.5))
            except Exception:
                pass
        else:  # tistory
            # Demand: emphasize long-tail and slight vol influence
            try:
                monthly_sum = ((getattr(m, "naver_monthly_pc", 0) or 0) + (getattr(m, "naver_monthly_mobile", 0) or 0)) if m else 0
                if monthly_sum > 0:
                    d = min(3.0, d + min(math.log10(1 + monthly_sum) * 0.25, 0.5))
            except Exception:
                pass
            # Competition: prioritize Google results (SERP breadth)
            try:
                g_tot = getattr(m, "google_total", None) if m else None
                if isinstance(g_tot, int):
                    c = max(0.5, min(_comp_from_results(g_tot), 2.5))
            except Exception:
                pass

        opp = max(d * 1.4 - c, 0.0)
        results.append(KeywordScore(keyword=kw, demand=round(d, 3), competition=round(c, 3), opportunity=round(opp, 3), provider_hits=hits))

    results.sort(key=lambda x: (x.opportunity, x.demand), reverse=True)
    return results
