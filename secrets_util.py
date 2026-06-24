# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Szyfrowanie wrażliwych danych (tokeny, hasła SMTP)
===================================================
Tokeny Telegram i hasła SMTP NIE powinny leżeć w bazie jawnym tekstem -
zwłaszcza na publicznym wdrożeniu (Streamlit Cloud), gdzie baza bywa
współdzielona między testerami.

Ten moduł szyfruje/odszyfrowuje sekrety symetrycznie (Fernet / AES).
Klucz pobierany jest w kolejności:
    1. st.secrets["ENCRYPTION_KEY"]      (zalecane na Streamlit Cloud)
    2. zmienna środowiskowa ENCRYPTION_KEY
    3. lokalny plik .encryption_key       (generowany automatycznie przy
       pierwszym uruchomieniu lokalnym)

Jak wygenerować klucz (raz):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
i wkleić go w Streamlit Cloud → Settings → Secrets jako:
    ENCRYPTION_KEY = "wklejony-klucz"

Jeśli klucza nie da się ustalić ani wygenerować, moduł degraduje się
do trybu "bez szyfrowania" (zwraca tekst bez zmian) - aplikacja nadal
działa, ale sekrety nie są chronione. Funkcja is_encryption_active()
pozwala UI pokazać ostrzeżenie.
"""
from __future__ import annotations

import os
from functools import lru_cache

_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".encryption_key")
# Prefiks pozwala rozpoznać, czy dany ciąg jest już zaszyfrowany przez nas.
_PREFIX = "enc::"


@lru_cache(maxsize=1)
def _get_fernet():
    """Zwraca obiekt Fernet albo None, jeśli nie da się ustalić klucza."""
    try:
        from cryptography.fernet import Fernet
    except Exception:
        return None

    key = _resolve_key()
    if not key:
        return None
    try:
        return Fernet(key)
    except Exception:
        return None


def _resolve_key() -> bytes | None:
    # 1. st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        if "ENCRYPTION_KEY" in st.secrets:
            return str(st.secrets["ENCRYPTION_KEY"]).encode()
    except Exception:
        pass

    # 2. zmienna środowiskowa
    env_key = os.environ.get("ENCRYPTION_KEY")
    if env_key:
        return env_key.encode()

    # 3. lokalny plik (wygeneruj, jeśli brak) - tylko do użytku lokalnego
    try:
        if os.path.exists(_KEY_FILE):
            with open(_KEY_FILE, "rb") as f:
                return f.read().strip()
        # wygeneruj nowy klucz lokalny
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key()
        try:
            with open(_KEY_FILE, "wb") as f:
                f.write(new_key)
            os.chmod(_KEY_FILE, 0o600)
        except Exception:
            pass  # np. system plików tylko-do-odczytu (Streamlit Cloud)
        return new_key
    except Exception:
        return None


def is_encryption_active() -> bool:
    """True, jeśli szyfrowanie sekretów faktycznie działa."""
    return _get_fernet() is not None


def encrypt(value: str | None) -> str | None:
    """Szyfruje wartość. Zwraca ciąg z prefiksem 'enc::'.

    Jeśli szyfrowanie niedostępne, zwraca wartość bez zmian (degradacja).
    Puste/None zwraca bez zmian.
    """
    if not value:
        return value
    if value.startswith(_PREFIX):
        return value  # już zaszyfrowane
    fernet = _get_fernet()
    if fernet is None:
        return value
    try:
        token = fernet.encrypt(value.encode()).decode()
        return _PREFIX + token
    except Exception:
        return value


def decrypt(value: str | None) -> str | None:
    """Odszyfrowuje wartość zaszyfrowaną przez encrypt().

    Wartości bez prefiksu 'enc::' (np. starsze, niezaszyfrowane) zwraca
    bez zmian - dzięki temu migracja jest bezbolesna.
    """
    if not value or not value.startswith(_PREFIX):
        return value
    fernet = _get_fernet()
    if fernet is None:
        return value  # nie mamy klucza - oddaj surowo (lepsze niż crash)
    try:
        token = value[len(_PREFIX):]
        return fernet.decrypt(token.encode()).decode()
    except Exception:
        return value
