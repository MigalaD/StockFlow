# Copyright (c) 2026 Damian Migała / StockFlow

"""
Zależność FastAPI dostarczająca język żądania.

Język czytamy z nagłówka Accept-Language wysyłanego przez frontend.
Router deklaruje go jawnie jako parametr:

    def get_something(lang: RequestLang):
        ...

Dzięki zależności (zamiast middleware + globalny stan) język jest
widoczny w sygnaturze funkcji i bezpieczny przy wielu workerach oraz
równoległych żądaniach — nie ma współdzielonej zmiennej, którą inny
request mógłby nadpisać w trakcie.
"""

from __future__ import annotations

import os
import sys
from typing import Annotated

from fastapi import Depends, Header

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from i18n import normalize_lang


def get_request_lang(accept_language: str | None = Header(default=None)) -> str:
    """Zwraca 'pl' albo 'en' na podstawie nagłówka Accept-Language."""
    return normalize_lang(accept_language)


RequestLang = Annotated[str, Depends(get_request_lang)]
