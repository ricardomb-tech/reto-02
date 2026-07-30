"""A small in-process circuit breaker for the Hugging Face upstream call.

No external dependency: consecutive failures trip the breaker OPEN, calls fail fast
while it's open, and after a cooldown one trial call (HALF_OPEN) decides whether to
close it again or keep it open. See ADR-0010 for the reasoning.
"""
import time

from prometheus_client import Counter

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"

BREAKER_TRIPS = Counter(
    "sentiment_circuit_breaker_trips_total", "Times the upstream circuit breaker opened."
)


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the breaker is open."""


class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_seconds: float):
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._state = CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._state == OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.reset_seconds:
                return HALF_OPEN
        return self._state

    def before_call(self) -> None:
        if self.state == OPEN:
            raise CircuitBreakerOpenError(
                "Upstream temporarily disabled after repeated failures. Try again shortly."
            )

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._state = CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            if self._state != OPEN:
                BREAKER_TRIPS.inc()
            self._state = OPEN
            self._opened_at = time.monotonic()
