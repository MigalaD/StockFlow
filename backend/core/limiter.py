# Copyright (c) 2026 Damian Migała / StockFlow

"""
Współdzielony limiter (slowapi) — importowany przez main.py i routery.

Wydzielony do osobnego modułu, by uniknąć importów cyklicznych:
routery potrzebują dekoratora @limiter.limit(), a main.py rejestruje
handler wyjątków i stan aplikacji.

Gdy slowapi nie jest zainstalowane, limiter degraduje się do no-op
(dekorator nic nie robi) — aplikacja działa, tylko bez limitów.
"""

from __future__ import annotations

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMITING_AVAILABLE = True

except ImportError:
    # Fallback: no-op limiter gdy slowapi niedostępne
    RATE_LIMITING_AVAILABLE = False

    class _NoOpLimiter:
        """Atrapa limitera — dekorator .limit() nic nie zmienia."""
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    limiter = _NoOpLimiter()  # type: ignore
