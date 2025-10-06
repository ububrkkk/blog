from blog_keyword_analyzer.scoring import (
    estimate_competition_score,
    estimate_demand_score,
    score_keywords,
)


def test_scoring_ranges():
    kw = "게이밍 의자 허리 아픈 사람 추천"
    d = estimate_demand_score(kw, provider_hits=3)
    c = estimate_competition_score(kw)
    assert 0.0 < d <= 3.0
    assert 0.5 <= c <= 2.5


def test_score_keywords_sorted():
    kws = [
        "게이밍 의자 추천",
        "게이밍 의자 가격 비교",
        "게이밍 의자 허리 아픈 사람 추천",
    ]
    res = score_keywords(kws, hit_counts={k: 2 for k in kws})
    assert len(res) == 3
    # sorted by opportunity desc
    assert res == sorted(res, key=lambda r: (r.opportunity, r.demand), reverse=True)
