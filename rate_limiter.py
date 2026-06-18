"""
Rate Limiter dla zapytań do Yahoo Finance
==========================================
Yahoo Finance nie ma oficjalnego API i agresywnie ogranicza ruch (HTTP 429
"Too Many Requests"). Przy skanowaniu wielu spółek równolegle łatwo trafić
na czasową blokadę IP.

Ten moduł udostępnia:
1. `TokenBucket` – thread-safe limiter przepustowości (X zapytań na sekundę).
2. `rate_limited` – dekorator, który przepuszcza wywołania przez globalny
   token bucket (czeka, jeśli limit został wyczerpany).
3. `with_backoff` – dekorator z wykładniczym backoffem, który reaguje na
   błędy typu 429/rate-limit dłuższą przerwą niż zwykły retry.

Dzięki temu nawet równoległy skaner (ThreadPoolExecutor) nie przekroczy
ustalonego tempa zapytań.
"""
from __future__ import annotations

import time
import threading
import functools


class TokenBucket:
    """Thread-safe token bucket.

    Pozwala na średnio `rate` operacji na sekundę, z możliwością chwilowych
    "zrywów" do `capacity` operacji. Tokeny odnawiają się w sposób ciągły.

    Przykład: TokenBucket(rate=8, capacity=8) -> ~8 zapytań/s, burst do 8.
    """

    def __init__(self, rate: float = 8.0, capacity: float | None = None):
        self.rate = float(rate)
        self.capacity = float(capacity if capacity is not None else rate)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)

    def acquire(self, tokens: float = 1.0, timeout: float | None = None) -> bool:
        """Pobiera `tokens` tokenów, czekając jeśli trzeba.

        Zwraca True gdy się udało; False jeśli przekroczono `timeout`.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                # ile czasu do uzbierania brakujących tokenów
                missing = tokens - self._tokens
                wait = missing / self.rate
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            time.sleep(max(wait, 0.005))


# Globalny limiter współdzielony przez wszystkie wątki skanera.
# 8 zapytań/s to bezpieczny kompromis dla Yahoo Finance.
import os as _os

# Globalny limiter współdzielony przez wszystkie wątki skanera.
# Domyślnie 8 zapytań/s. Na publicznym wdrożeniu (jedno wspólne IP, wielu
# użytkowników naraz) warto zejść niżej - ustaw zmienną środowiskową
# YF_RATE_LIMIT (np. =4) albo sekret Streamlit o tej nazwie.
def _initial_rate() -> float:
    try:
        val = _os.environ.get("YF_RATE_LIMIT")
        if val:
            return max(1.0, float(val))
    except Exception:
        pass
    return 8.0


_RATE = _initial_rate()
_GLOBAL_BUCKET = TokenBucket(rate=_RATE, capacity=_RATE)


def set_global_rate(rate: float, capacity: float | None = None):
    """Pozwala dostroić globalne tempo (np. wolniej, jeśli łapiesz 429)."""
    global _GLOBAL_BUCKET
    _GLOBAL_BUCKET = TokenBucket(rate=rate, capacity=capacity)


def rate_limited(func):
    """Dekorator: przepuszcza wywołania przez globalny token bucket."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _GLOBAL_BUCKET.acquire()
        return func(*args, **kwargs)
    return wrapper


def _looks_like_rate_limit(exc: Exception) -> bool:
    """Heurystyka: czy wyjątek wygląda na rate-limit (HTTP 429)?"""
    text = str(exc).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text


def with_backoff(
    times: int = 4,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    rate_limit_penalty: float = 3.0,
):
    """Dekorator retry z wykładniczym backoffem.

    Przy błędach wyglądających na rate-limit (429) czeka `rate_limit_penalty`×
    dłużej niż przy zwykłym błędzie, żeby dać serwerowi czas ochłonąć.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            wait = base_delay
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt >= times:
                        break
                    is_rate_limit = _looks_like_rate_limit(e)
                    penalty = rate_limit_penalty if is_rate_limit else 1.0
                    if is_rate_limit:
                        _log_rate_limit(func.__name__, attempt, wait * penalty)
                    time.sleep(wait * penalty)
                    wait *= backoff
            raise last_exc
        return wrapper
    return decorator


def _log_rate_limit(func_name: str, attempt: int, wait: float):
    """Loguje wykryty rate-limit (jeśli moduł logowania jest dostępny)."""
    try:
        from app_logging import get_logger
        get_logger("rate_limiter").warning(
            "Rate limit w %s (próba %d) - czekam %.1fs", func_name, attempt, wait
        )
    except Exception:
        pass
