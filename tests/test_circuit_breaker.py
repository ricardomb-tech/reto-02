import time

import pytest

from app.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


def test_starts_closed_and_allows_calls():
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30)
    breaker.before_call()  # should not raise


def test_opens_after_reaching_failure_threshold():
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=30)
    breaker.record_failure()
    breaker.before_call()  # still closed, one failure short of the threshold

    breaker.record_failure()
    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_call()


def test_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=30)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    breaker.before_call()  # only one failure since the reset, still closed


def test_half_open_after_cooldown_allows_a_trial_call():
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=0.1)
    breaker.record_failure()
    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_call()

    time.sleep(0.25)
    breaker.before_call()  # cooldown elapsed, half-open trial call allowed


def test_half_open_failure_reopens_the_breaker():
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=0.1)
    breaker.record_failure()
    time.sleep(0.25)
    breaker.before_call()  # half-open trial

    breaker.record_failure()
    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_call()
