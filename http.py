from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional

import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


class HttpClient:
    """Lightweight HTTP client with retries and jitter."""

    def __init__(
        self,
        timeout: float = 8.0,
        max_retries: int = 2,
        min_delay: float = 0.2,
        max_delay: float = 0.7,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        if headers:
            self.session.headers.update(headers)

    def _sleep_jitter(self) -> None:
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        last_exc: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._sleep_jitter()
        if last_exc:
            raise last_exc

    def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        last_exc: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._sleep_jitter()
        if last_exc:
            raise last_exc

