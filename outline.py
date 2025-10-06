from __future__ import annotations

from typing import Dict, List

from .text_utils import tokenize


def build_outline(keyword: str) -> Dict[str, List[str]]:
    """Create a simple content outline (title/H2/FAQ) for a keyword."""
    toks = tokenize(keyword)
    head = keyword
    h1 = f"{head} 총정리"
    h2s = [
        f"{head} 한눈에 보기",
        f"{head} 핵심 체크리스트",
        f"{head} 자주 겪는 문제와 해결",
        f"{head} 비교/대안 살펴보기",
        f"{head} 최종 선택 가이드",
    ]
    faq = [
        f"Q. {head} 초보도 쉽게 할 수 있나요?",
        f"Q. {head} 할 때 꼭 피해야 할 점은?",
        f"Q. {head} 비용(가격)을 줄이는 팁은?",
        f"Q. {head} 대체 키워드/연관 주제는?",
    ]
    # Slight variation based on modifiers
    if any(t in ("가격", "할인", "쿠폰", "비교", "추천") for t in toks):
        h2s.insert(1, f"{head} 가격대/가성비 분류")
    if any(t in ("방법", "설정", "가이드") for t in toks):
        h2s.insert(1, f"{head} 단계별 따라하기")

    return {"title": [h1], "sections": h2s[:7], "faq": faq[:6]}

