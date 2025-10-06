from blog_keyword_analyzer.expansion import expand_with_profile, expand_with_suffixes


def test_profile_travel_adds_variants():
    seeds = ["제주"]
    out = expand_with_profile(seeds, "travel")
    assert any("여행" in kw for kw in out)
    assert any("2박3일" in kw for kw in out)


def test_profile_food_adds_variants():
    seeds = ["부산"]
    out = expand_with_profile(seeds, "food")
    assert any("맛집" in kw for kw in out)
    assert any("예약" in kw for kw in out)

