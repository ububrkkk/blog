from __future__ import annotations

from typing import Iterable, List

from .text_utils import normalize_query, unique_ordered


KOREAN_LONGTAIL_SUFFIXES = [
    "방법",
    "후기",
    "리뷰",
    "비교",
    "추천",
    "가격",
    "요령",
    "설정",
    "문제",
    "고장",
    "가이드",
    "구매팁",
    "사용기",
    "주의사항",
    "단점",
    "장점",
    "필수 설정",
    "초보 가이드",
]


def append_suffixes(seed: str, suffixes: Iterable[str] | None = None) -> List[str]:
    suffixes = list(suffixes) if suffixes is not None else KOREAN_LONGTAIL_SUFFIXES
    out = [normalize_query(f"{seed} {suf}") for suf in suffixes]
    return unique_ordered(out)


def expand_with_suffixes(seeds: Iterable[str], suffixes: Iterable[str] | None = None) -> List[str]:
    out: List[str] = []
    for s in seeds:
        out.extend(append_suffixes(s, suffixes=suffixes))
    return unique_ordered(out)


# Domain-specific profiles for travel and food/restaurant blogs
PROFILE_SUFFIXES = {
    "travel": [
        "여행", "여행 코스", "여행 일정", "루트", "코스", "일정",
        "2박3일", "3박4일", "1일 코스", "주말여행", "근교", "당일치기",
        "핫플", "포토스팟", "인생샷", "노을", "야경", "전망대",
        "성수기", "비수기", "날씨", "옷차림", "렌터카", "대중교통", "주차",
        "숙소", "호텔", "게하", "펜션", "캠핑", "카페", "맛집", "베스트",
        "추천", "비용", "예산", "꿀팁", "주의사항",
    ],
    "food": [
        "맛집", "핫플", "카페", "디저트", "베이커리",
        "메뉴", "가격", "가성비", "코스", "예약", "웨이팅", "영업시간",
        "브런치", "런치", "디너", "주차", "분위기", "데이트", "회식",
        "혼밥", "단체", "포장", "배달", "리뷰", "후기", "추천",
        "근처 맛집", "역 근처", "OO동 맛집", "OO역 맛집",
    ],
}


def expand_with_profile(seeds: Iterable[str], profile: str) -> List[str]:
    profile = profile.lower()
    suffixes = PROFILE_SUFFIXES.get(profile, [])
    if not suffixes:
        return unique_ordered(list(seeds))
    return unique_ordered(expand_with_suffixes(seeds, suffixes=suffixes))
