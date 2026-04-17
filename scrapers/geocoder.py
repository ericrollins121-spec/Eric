import time
from threading import Lock
from typing import Optional, Tuple

import requests

from .cache import TTLCache


class Geocoder:
    """
    Thin wrapper around the Nominatim (OpenStreetMap) geocoding API.

    Nominatim's usage policy requires:
      - max 1 request per second per IP
      - a descriptive User-Agent identifying the app and a contact
      - aggressive caching of results (locations don't move)

    We enforce all three: a process-wide lock that throttles to 1 req/s,
    a long-TTL in-memory cache keyed by the raw query, and a UA.
    """

    URL = "https://nominatim.openstreetmap.org/search"
    UA = "RentalSearchApp/1.0 (+https://example.com/contact)"

    def __init__(self, ttl_seconds: int = 7 * 24 * 3600):
        self._cache = TTLCache(ttl_seconds=ttl_seconds, max_entries=4096)
        self._rate_lock = Lock()
        self._last_call: float = 0.0

    def lookup(
        self, query: str, city_hint: Optional[str] = None
    ) -> Optional[Tuple[float, float]]:
        if not query or not query.strip():
            return None
        q = query.strip()
        if city_hint and city_hint.lower() not in q.lower():
            q = f"{q}, {city_hint}"

        return self._cache.get_or_set(q, lambda: self._fetch(q))

    def _fetch(self, q: str) -> Optional[Tuple[float, float]]:
        # Rate-limit: at least 1.1 seconds between live calls.
        with self._rate_lock:
            wait = 1.1 - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()

        try:
            resp = requests.get(
                self.URL,
                params={"q": q, "format": "json", "limit": 1},
                headers={"User-Agent": self.UA, "Accept-Language": "en"},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            return (float(data[0]["lat"]), float(data[0]["lon"]))
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return None
