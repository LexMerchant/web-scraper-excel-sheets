"""HTTP-клиент: повторы при ошибках, пауза между запросами, нормальный User-Agent."""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.9",
}


class Client:
    def __init__(self, delay: float = 0.5, retries: int = 3, timeout: float = 20):
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._last_request = 0.0

    def get(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            self._wait()
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                # Если сервер не указал кодировку, requests считает её latin-1 —
                # тогда определяем по содержимому, иначе кириллица и «£» побьются
                if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except requests.RequestException as exc:
                last_error = exc
                backoff = 2 ** attempt
                log.warning("Ошибка %s (попытка %d/%d), жду %d с", exc, attempt, self.retries, backoff)
                time.sleep(backoff)
        raise RuntimeError(f"Не удалось загрузить {url}: {last_error}")

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.monotonic()
