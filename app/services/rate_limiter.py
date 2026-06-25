import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int | None = None


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            self._prune_stale_keys(cutoff)
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.limit:
                wait = self.window_seconds - (now - events[0])
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=max(1, math.ceil(wait)),
                )

            events.append(now)
            return RateLimitDecision(allowed=True)

    def _prune_stale_keys(self, cutoff: float) -> None:
        stale_keys = [
            key for key, events in self._events.items() if not events or events[-1] <= cutoff
        ]
        for key in stale_keys:
            self._events.pop(key, None)
