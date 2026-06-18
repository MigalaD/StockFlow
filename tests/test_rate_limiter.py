"""
Testy dla rate_limiter.py
==========================
Sprawdzają token bucket (przepustowość, thread-safety) oraz dekoratory
rate_limited i with_backoff.
"""
import time
import threading

import pytest

from rate_limiter import (
    TokenBucket, rate_limited, with_backoff, _looks_like_rate_limit,
)


def test_token_bucket_immediate_capacity():
    # Bucket pełny na starcie - powinien od razu wydać `capacity` tokenów
    bucket = TokenBucket(rate=100, capacity=5)
    start = time.monotonic()
    for _ in range(5):
        assert bucket.acquire(timeout=1.0)
    elapsed = time.monotonic() - start
    # 5 tokenów z pełnego bufora powinno pójść niemal natychmiast
    assert elapsed < 0.2


def test_token_bucket_throttles_beyond_capacity():
    # rate=10/s, capacity=1: drugi token musi poczekać ~0.1s
    bucket = TokenBucket(rate=10, capacity=1)
    bucket.acquire()  # zużywa początkowy token
    start = time.monotonic()
    bucket.acquire()  # musi poczekać na odnowienie
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05  # ~0.1s, z marginesem


def test_token_bucket_timeout_returns_false():
    bucket = TokenBucket(rate=1, capacity=1)
    bucket.acquire()  # zużyj token
    # następny token potrzebuje 1s, ale dajemy tylko 0.05s
    assert bucket.acquire(timeout=0.05) is False


def test_token_bucket_thread_safety():
    # 20 wątków pobiera po 1 tokenie; rate wysoki, capacity duży -> wszystkie OK
    bucket = TokenBucket(rate=1000, capacity=20)
    results = []
    lock = threading.Lock()

    def worker():
        ok = bucket.acquire(timeout=2.0)
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 20
    assert all(results)


def test_rate_limited_decorator_passes_through():
    @rate_limited
    def add(a, b):
        return a + b
    assert add(2, 3) == 5


def test_with_backoff_retries_then_succeeds():
    calls = {"n": 0}

    @with_backoff(times=3, base_delay=0.01)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("temporary")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_with_backoff_gives_up_and_raises():
    @with_backoff(times=2, base_delay=0.01)
    def always_fails():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        always_fails()


def test_looks_like_rate_limit_detection():
    assert _looks_like_rate_limit(Exception("HTTP 429 Too Many Requests"))
    assert _looks_like_rate_limit(Exception("rate limit exceeded"))
    assert not _looks_like_rate_limit(Exception("connection reset"))
