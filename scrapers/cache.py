import time
from threading import Lock
from typing import Any, Callable, Dict, Tuple


class TTLCache:
    """Tiny thread-safe in-memory TTL cache.

    Good enough for rate-limiting upstream scrape calls during a session;
    not a substitute for a real cache (Redis, etc.) in production.
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 256):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._store: Dict[Any, Tuple[float, Any]] = {}
        self._lock = Lock()

    def get_or_set(self, key: Any, producer: Callable[[], Any]) -> Any:
        now = time.time()
        with self._lock:
            hit = self._store.get(key)
            if hit and now - hit[0] < self.ttl:
                return hit[1]

        value = producer()

        with self._lock:
            if len(self._store) >= self.max_entries:
                oldest = min(self._store.items(), key=lambda kv: kv[1][0])[0]
                self._store.pop(oldest, None)
            self._store[key] = (now, value)
        return value
