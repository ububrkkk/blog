from __future__ import annotations

import csv
import io
import os
import sys
from typing import Dict, List, Tuple

import streamlit as st

# Allow running as a script (streamlit run ...) without PYTHONPATH set
_SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from blog_keyword_analyzer.env import load_env  # type: ignore
from blog_keyword_analyzer.expansion import expand_with_profile, expand_with_suffixes  # type: ignore
from blog_keyword_analyzer.outline import build_outline  # type: ignore
from blog_keyword_analyzer.providers import GoogleSuggestProvider, NaverSuggestProvider  # type: ignore
from blog_keyword_analyzer.scoring import (  # type: ignore
    KeywordScore,
    score_keywords,
    score_keywords_with_metrics,
    score_keywords_by_platform,
)
from blog_keyword_analyzer.text_utils import normalize_query, unique_ordered  # type: ignore
from blog_keyword_analyzer.enrichers import build_enrichers_from_env, enrich_keywords, EnrichedMetrics  # type: ignore


@st.cache_data(show_spinner=False)
def collect_suggestions_cached(
    seeds: List[str], provider_names: List[str], depth: int, hl: str
) -> Tuple[List[str], Dict[str, int]]:
    provider_names = [p.strip().lower() for p in provider_names]
    providers = []
    if "naver" in provider_names:
        providers.append(NaverSuggestProvider())
    if "google" in provider_names:
        providers.append(GoogleSuggestProvider())

    all_candidates: List[str] = []
    hit_counts: Dict[str, int] = {}

    def _accumulate(cands: List[str]) -> None:
        for kw in cands:
            all_candidates.append(kw)
            hit_counts[kw] = hit_counts.get(kw, 0) + 1

    # depth 1
    for p in providers:
        if isinstance(p, GoogleSuggestProvider):
            _accumulate(p.bulk_suggest(seeds, hl=hl))
        else:
            _accumulate(p.bulk_suggest(seeds))

    # depth 2
    if depth >= 2:
        suffix_expanded = expand_with_suffixes(seeds)
        for p in providers:
            if isinstance(p, GoogleSuggestProvider):
                _accumulate(p.bulk_suggest(suffix_expanded, hl=hl))
            else:
                _accumulate(p.bulk_suggest(suffix_expanded))

    return unique_ordered(all_candidates), hit_counts


def to_rows(scores: List[KeywordScore], metrics: Dict[str, EnrichedMetrics] | None) -> List[dict]:
    data: List[dict] = []
    for r in scores:
        row = {
            "keyword": r.keyword,
            "opportunity": r.opportunity,
            "demand": r.demand,
            "competition": r.competition,
            "provider_hits": r.provider_hits,
        }
        if metrics is not None:
            m = metrics.get(r.keyword)
            row.update(
                {
                    "naver_blog_total": getattr(m, "naver_blog_total", None) if m else None,
                    "google_total": getattr(m, "google_total", None) if m else None,
                    "naver_monthly_pc": getattr(m, "naver_monthly_pc", None) if m else None,
                    "naver_monthly_mobile": getattr(m, "naver_monthly_mobile", None) if m else None,
                    "naver_cpc": getattr(m, "naver_cpc", None) if m else None,
                }
            )
        data.append(row)
    return data


def to_csv_bytes(rows: List[dict]) -> bytes:
    buf = io.StringIO()
    if not rows:
        return b""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue().encode("utf-8-sig")


def main() -> None:
    load_env()
    st.set_page_config(page_title="블로그 키워드 분석기", layout="wide")
    st.title("블로그 키워드 분석기 (Naver/Tistory)")

    with st.sidebar:
        st.header("설정")
        providers = st.multiselect("Providers", ["naver", "google"], default=["naver", "google"])
        depth = st.slider("Depth", 1, 2, 2)
        profile = st.selectbox("Profile", ["", "travel", "food"], index=0)
        include_suffix = st.checkbox("롱테일 접미사 포함", value=False)
        limit = st.number_input("최대 후보 수", min_value=50, max_value=2000, value=400, step=50)
        top = st.number_input("상위 미리보기", min_value=10, max_value=300, value=80, step=10)
        enrich = st.checkbox("API 보정 활용(--enrich)", value=False)
        enrich_limit = st.number_input("Enrich 상한", min_value=50, max_value=1000, value=200, step=50)

    seeds_text = st.text_area("시드 키워드 (줄 단위)", "제주 여행\n부산 맛집")
    run = st.button("실행")

    if run:
        seeds = [normalize_query(s) for s in seeds_text.splitlines() if normalize_query(s)]
        if not seeds:
            st.warning("시드 키워드를 1개 이상 입력하세요.")
            return
        if not providers:
            providers_use = ["google"]
        else:
            providers_use = providers

        with st.spinner("제안 수집 중..."):
            try:
                candidates, hit_counts = collect_suggestions_cached(seeds, providers_use, depth=depth, hl="ko")
            except Exception as e:  # noqa: BLE001
                st.error(f"제안 수집 오류: {e}")
                return

        if profile:
            candidates = unique_ordered(candidates + expand_with_profile(seeds, profile))
        elif include_suffix:
            candidates = unique_ordered(candidates + expand_with_suffixes(seeds))
        if limit:
            candidates = candidates[: int(limit)]

        st.info(f"후보 {len(candidates)}개 점수화 중...")
        metrics_map: Dict[str, EnrichedMetrics] | None = None
        try:
            if enrich:
                enrichers = build_enrichers_from_env()
                if not enrichers:
                    st.warning("ENV에 API 키가 없어 휴리스틱으로 진행합니다(.env를 설정하세요).")
                metrics_map = enrich_keywords(candidates, enrichers, limit=int(enrich_limit))
                scores = score_keywords_with_metrics(candidates, hit_counts=hit_counts, metrics=metrics_map)
            else:
                scores = score_keywords(candidates, hit_counts=hit_counts)
        except Exception as e:  # noqa: BLE001
            st.error(f"점수화 오류: {e}")
            return

        rows = to_rows(scores, metrics_map)
        st.subheader("결과")
        st.dataframe(rows[: int(top)], use_container_width=True)

        csv_bytes = to_csv_bytes(rows)
        st.download_button(
            "CSV 다운로드",
            data=csv_bytes,
            file_name="results.csv",
            mime="text/csv",
        )

        # Outline helper for first top result
        if rows:
            sel_kw = rows[0]["keyword"]
            with st.expander(f"아웃라인 미리보기: {sel_kw}"):
                outline = build_outline(sel_kw)
                st.write("제목:", outline["title"][0])
                st.write("섹션:")
                for s in outline["sections"]:
                    st.write("- ", s)
                st.write("FAQ:")
                for q in outline["faq"]:
                    st.write("- ", q)


if __name__ == "__main__":  # pragma: no cover
    main()
