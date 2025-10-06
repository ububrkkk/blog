from blog_keyword_analyzer.text_utils import (
    normalize_query,
    tokenize,
    unique_ordered,
)


def test_normalize_and_tokenize():
    s = "  게이밍   의자\n가격\t비교  "
    norm = normalize_query(s)
    assert norm == "게이밍 의자 가격 비교"
    toks = tokenize(norm)
    assert toks == ["게이밍", "의자", "가격", "비교"]


def test_unique_ordered():
    items = ["a", "b", "a", "c", "b"]
    assert unique_ordered(items) == ["a", "b", "c"]
