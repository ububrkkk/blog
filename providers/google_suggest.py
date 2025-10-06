from __future__ import annotations

from typing import Iterable, List

from ..http import HttpClient
from ..text_utils import normalize_query, unique_ordered


class GoogleSuggestProvider:
    """Fetch suggestions from Google suggest endpoint.

    Uses the `client=firefox` JSON-compatible API.
    """

    BASE_URL = "https://suggestqueries.google.com/complete/search"

    def __init__(self, http: HttpClient | None = None) -> None:
        self.http = http or HttpClient()

    def suggest(self, seed: str, hl: str = "ko") -> List[str]:
        params = {"client": "firefox", "q": seed, "hl": hl}
        data = self.http.get_json(self.BASE_URL, params=params)
        # Response shape: [query, [suggest1, suggest2, ...], ...]
        if not isinstance(data, list) or len(data) < 2:
            return []
        suggestions = data[1] or []
        cleaned = [normalize_query(s) for s in suggestions if isinstance(s, str)]
        return unique_ordered([s for s in cleaned if s and s != seed])

    def bulk_suggest(self, seeds: Iterable[str], hl: str = "ko") -> List[str]:
        out: List[str] = []
        for seed in seeds:
            out.extend(self.suggest(seed, hl=hl))
        return unique_ordered(out)

