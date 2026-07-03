# Copyright (c) 2026 Damian Migała / StockFlow

"""
Przeliczanie walut — kursy z Frankfurter (referencyjne kursy EBC).

Frankfurter: https://frankfurter.dev
- Bez klucza API, bez limitów, open source
- Kursy referencyjne Europejskiego Banku Centralnego (aktualizowane raz dziennie ~16:00 CET)
- Idealne do WYŚWIETLANIA wartości portfela (nie do handlu — brak spreadu bid/ask)

Kursy cache'owane w pamięci na 12h — EBC i tak publikuje raz dziennie,
więc częstsze odpytywanie nie ma sensu i tylko obciążałoby API.
"""

from __future__ import annotations

import logging
import time
import requests

log = logging.getLogger("stockflow.currency")

_FRANKFURTER_BASE = "https://api.frankfurter.dev/v1"
_TIMEOUT = 8
_CACHE_TTL = 12 * 3600  # 12h

# Cache: {base_currency: (timestamp, {waluta: kurs})}
_rates_cache: dict[str, tuple[float, dict[str, float]]] = {}

# Waluty pegowane / nieobsługiwane przez EBC — traktujemy 1:1 lub pomijamy.
# (EBC nie publikuje np. niektórych walut egzotycznych)
_SUPPORTED_HINT = {
    "EUR", "USD", "PLN", "GBP", "CHF", "JPY", "NOK", "SEK", "DKK",
    "CZK", "HUF", "CAD", "AUD", "CNY", "HKD", "SGD", "TRY", "RON",
}


def get_rates(base: str = "EUR") -> dict[str, float] | None:
    """Zwraca kursy: ile jednostek danej waluty za 1 jednostkę `base`.
    Np. get_rates('USD')['PLN'] = ile PLN za 1 USD. None przy błędzie."""
    base = base.upper().strip()
    now = time.time()

    cached = _rates_cache.get(base)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]

    try:
        resp = requests.get(
            f"{_FRANKFURTER_BASE}/latest",
            params={"base": base},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        if not rates:
            return cached[1] if cached else None
        # Waluta bazowa względem samej siebie = 1.0
        rates[base] = 1.0
        _rates_cache[base] = (now, rates)
        return rates
    except Exception as e:
        log.warning("Frankfurter: błąd pobierania kursów dla %s: %s", base, e)
        # Zwróć stary cache jeśli jest (lepszy nieaktualny kurs niż żaden)
        return cached[1] if cached else None


def convert(amount: float, from_ccy: str, to_ccy: str) -> float | None:
    """Przelicza `amount` z waluty `from_ccy` na `to_ccy`.
    Zwraca None gdy brak kursu (np. brak połączenia i pusty cache)."""
    from_ccy = from_ccy.upper().strip()
    to_ccy   = to_ccy.upper().strip()

    if from_ccy == to_ccy:
        return amount

    # Pobierz kursy z bazą = waluta docelowa, wtedy rate[from] mówi
    # ile `to` za 1 `from`... a właściwie odwrotnie. Prościej: baza = from.
    rates = get_rates(from_ccy)
    if not rates or to_ccy not in rates:
        return None
    return round(amount * rates[to_ccy], 2)


def convert_many(items: list[tuple[float, str]], to_ccy: str) -> float | None:
    """Sumuje listę (kwota, waluta) przeliczoną na `to_ccy`.
    Zwraca None jeśli KTÓREJKOLWIEK pozycji nie da się przeliczyć
    (lepiej pokazać 'brak danych' niż błędną sumę)."""
    to_ccy = to_ccy.upper().strip()
    total = 0.0
    for amount, ccy in items:
        converted = convert(amount, ccy, to_ccy)
        if converted is None:
            return None
        total += converted
    return round(total, 2)
