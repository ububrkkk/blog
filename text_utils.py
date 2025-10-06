from __future__ import annotations

import re
from typing import Iterable, List, Set


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[\t\r\n\v\f]+")


def normalize_query(q: str) -> str:
    """Normalize a query for de-duplication and display.

    - Trim and collapse whitespace
    - Strip control characters
    - Keep Korean letters as-is; do not lowercase (not meaningful for ko)
    """
    q = q.strip()
    q = _PUNCT_RE.sub(" ", q)
    q = _WS_RE.sub(" ", q)
    return q


def tokenize(q: str) -> List[str]:
    """Very simple whitespace tokenizer for Korean/English mixed text."""
    q = normalize_query(q)
    return [tok for tok in q.split(" ") if tok]


def unique_ordered(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out

