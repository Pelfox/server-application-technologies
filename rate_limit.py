from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, rule: RateLimitRule) -> None:
        current_time = monotonic()
        window_start = current_time - rule.window_seconds

        with self._lock:
            request_times = self._requests[key]
            while request_times and request_times[0] <= window_start:
                request_times.popleft()

            if len(request_times) >= rule.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                )

            request_times.append(current_time)


def create_rate_limit_dependency(
    limiter: InMemoryRateLimiter,
    scope: str,
    rule: RateLimitRule,
):
    def rate_limit(request: Request) -> None:
        client_host = request.client.host if request.client is not None else "unknown"
        limiter.check(f"{scope}:{client_host}", rule)

    return rate_limit
