from __future__ import annotations

import argparse
import csv
from typing import Dict, Iterable, List, Optional, Tuple

from .expansion import expand_with_suffixes, expand_with_profile
from .outline import build_outline
from .providers import GoogleSuggestProvider, NaverSuggestProvider
from .scoring import KeywordScore, score_keywords, score_keywords_with_metrics, score_keywords_by_platform
from .text_utils import normalize_query, unique_ordered
from .enrichers import build_enrichers_from_env, enrich_keywords, EnrichedMetrics
from .env import load_env


def _read_seeds(seed_args: List[str], seed_file: Optional[str]) -> List[str]:
    seeds: List[str] = []
    if seed_args:
        seeds.extend(seed_args)
    if seed_file:
        with open(seed_file, "r", encoding="utf-8") as f:
            for line in f:
                s = normalize_query(line)
                if s:
                    seeds.append(s)
    return unique_ordered([s for s in seeds if s])


def _collect_suggestions(
    seeds: Iterable[str], provider_names: List[str], depth: int, hl: str
) -> Tuple[List[str], Dict[str, int]]:
    provider_names = [p.strip().lower() for p in provider_names]
    providers = []
    if "naver" in provider_names:
        providers.append(NaverSuggestProvider())
    if "google" in provider_names:
        providers.append(GoogleSuggestProvider())

    # Depth 1: providers over seeds
    all_candidates: List[str] = []
    hit_counts: Dict[str, int] = {}

    def _accumulate(cands: Iterable[str]) -> None:
        for kw in cands:
            all_candidates.append(kw)
            hit_counts[kw] = hit_counts.get(kw, 0) + 1

    # round 1
    for p in providers:
        if isinstance(p, GoogleSuggestProvider):
            _accumulate(p.bulk_suggest(seeds, hl=hl))
        else:
            _accumulate(p.bulk_suggest(seeds))

    if depth >= 2:
        # expand with suffixes and query again
        suffix_expanded = expand_with_suffixes(seeds)
        for p in providers:
            if isinstance(p, GoogleSuggestProvider):
                _accumulate(p.bulk_suggest(suffix_expanded, hl=hl))
            else:
                _accumulate(p.bulk_suggest(suffix_expanded))

    return unique_ordered(all_candidates), hit_counts


def cmd_analyze(args: argparse.Namespace) -> int:
    seeds = _read_seeds(args.seeds, args.seed_file)
    if not seeds:
        print("[!] 시드 키워드를 1개 이상 입력하세요.")
        return 2

    candidates, hit_counts = _collect_suggestions(
        seeds=seeds, provider_names=args.providers.split(","), depth=args.depth, hl=args.hl
    )

    if args.profile:
        candidates = unique_ordered(candidates + expand_with_profile(seeds, args.profile))
    elif args.include_suffix:
        candidates = unique_ordered(candidates + expand_with_suffixes(seeds))

    if args.limit:
        candidates = candidates[: args.limit]

    scores: List[KeywordScore]
    metrics_map: Dict[str, EnrichedMetrics] | None = None
    if args.enrich:
        enrichers = build_enrichers_from_env()
        if not enrichers:
            print("[!] 활성화된 API 자격이 없습니다. ENV 설정을 확인하세요. (NAVER_* / GOOGLE_*)")
        metrics_map = enrich_keywords(candidates, enrichers, limit=args.enrich_limit)
        scores = score_keywords_with_metrics(candidates, hit_counts=hit_counts, metrics=metrics_map)
    else:
        scores = score_keywords(candidates, hit_counts=hit_counts)

    platforms = [p.strip().lower() for p in (args.platforms or "").split(",") if p.strip()]
    if not platforms:
        # default: both views
        platforms = ["naver", "tistory"]

    if len(platforms) == 1 and platforms[0] in ("all", "combined"):
        platforms = ["naver", "tistory"]

    # If platform split requested, compute per platform results
    if platforms:
        per_platform: Dict[str, List[KeywordScore]] = {}
        for pf in platforms:
            if args.enrich and metrics_map is not None:
                per_platform[pf] = score_keywords_by_platform(candidates, hit_counts=hit_counts, metrics=metrics_map, platform=pf)
            else:
                # Without metrics, use baseline then reuse as same for both
                per_platform[pf] = score_keywords(candidates, hit_counts=hit_counts)

        for pf in platforms:
            pf_scores = per_platform[pf]
            top_n = args.top or min(50, len(pf_scores))
            print(f"[i] [{pf.upper()}] 총 후보 {len(pf_scores)}개. 상위 {top_n}개:")
            for row in pf_scores[:top_n]:
                print(
                    f"- {row.keyword} | 기회 {row.opportunity:.2f} / 수요 {row.demand:.2f} / 경쟁 {row.competition:.2f} (hits {row.provider_hits})"
                )

        if args.output:
            out = args.output
            # derive prefix if endswith .csv
            prefix = out[:-4] if out.lower().endswith(".csv") else out
            for pf in platforms:
                path = f"{prefix}.{pf}.csv"
                _write_csv(path, per_platform[pf], metrics_map)
                print(f"[i] [{pf.upper()}] CSV 저장 완료: {path}")
    else:
        # Fallback single combined
        top_n = args.top or min(50, len(scores))
        print(f"[i] 총 후보 {len(scores)}개. 상위 {top_n}개 미리보기:")
        for row in scores[:top_n]:
            print(
                f"- {row.keyword} | 기회 {row.opportunity:.2f} / 수요 {row.demand:.2f} / 경쟁 {row.competition:.2f} (hits {row.provider_hits})"
            )
        if args.output:
            _write_csv(args.output, scores, metrics_map)
            print(f"[i] CSV 저장 완료: {args.output}")

    return 0


def _write_csv(path: str, rows: List[KeywordScore], metrics: Optional[Dict[str, EnrichedMetrics]] = None) -> None:
    # Use UTF-8 with BOM for better Excel compatibility on Windows
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        header = ["keyword", "opportunity", "demand", "competition", "provider_hits"]
        if metrics is not None:
            header += [
                "naver_blog_total",
                "google_total",
                "naver_monthly_pc",
                "naver_monthly_mobile",
                "naver_cpc",
            ]
        writer.writerow(header)
        for r in rows:
            row = [r.keyword, r.opportunity, r.demand, r.competition, r.provider_hits]
            if metrics is not None:
                m = metrics.get(r.keyword)
                row += [
                    getattr(m, "naver_blog_total", None) if m else None,
                    getattr(m, "google_total", None) if m else None,
                    getattr(m, "naver_monthly_pc", None) if m else None,
                    getattr(m, "naver_monthly_mobile", None) if m else None,
                    getattr(m, "naver_cpc", None) if m else None,
                ]
            writer.writerow(row)


def cmd_outline(args: argparse.Namespace) -> int:
    info = build_outline(args.keyword)
    print(f"제목: {info['title'][0]}")
    print("섹션:")
    for h2 in info["sections"]:
        print(f"- {h2}")
    print("FAQ:")
    for q in info["faq"]:
        print(f"- {q}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Naver/Tistory 블로그 키워드 분석기")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="시드에서 키워드를 확장/점수화")
    a.add_argument("--seeds", nargs="*", default=[], help="시드 키워드 리스트")
    a.add_argument("--seed-file", default=None, help="줄 단위 시드 키워드 파일")
    a.add_argument("--providers", default="naver,google", help="사용할 provider (naver,google)")
    a.add_argument("--depth", type=int, default=2, help="확장 깊이(1~2)")
    a.add_argument("--include-suffix", action="store_true", help="롱테일 접미사 확장 포함")
    a.add_argument("--profile", choices=["travel", "food"], help="도메인 프로필 기반 확장(여행/맛집)")
    a.add_argument("--limit", type=int, default=500, help="최대 후보 수")
    a.add_argument("--top", type=int, default=50, help="터미널 상위 출력 개수")
    a.add_argument("--output", default=None, help="CSV 저장 경로")
    a.add_argument("--hl", default="ko", help="Google suggest 언어 코드")
    a.add_argument("--enrich", action="store_true", help="API 연동으로 볼륨/경쟁 보정(Naver Ads/OpenAPI, Google CSE)")
    a.add_argument("--enrich-limit", type=int, default=200, help="API 조회 상한(키워드 상위 N개)")
    a.add_argument("--platforms", default="naver,tistory", help="플랫폼 별 결과(nav er,tistory). 여러 개 쉼표로 구분. 결과 파일은 각각 .naver/.tistory로 저장")
    a.set_defaults(func=cmd_analyze)

    o = sub.add_parser("outline", help="키워드 아웃라인 생성")
    o.add_argument("--keyword", required=True, help="아웃라인 생성 대상 키워드")
    o.set_defaults(func=cmd_outline)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Load .env if available for API keys
    load_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return int(func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
