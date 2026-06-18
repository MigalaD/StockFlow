"""
Testy dla secrets_util.py
==========================
Sprawdzają szyfrowanie/odszyfrowanie sekretów oraz bezpieczną degradację,
gdy klucz/biblioteka są niedostępne.
"""
import secrets_util as su


def test_encrypt_decrypt_roundtrip():
    su._get_fernet.cache_clear()
    original = "my-secret-telegram-token"
    enc = su.encrypt(original)
    # zaszyfrowany ciąg ma prefiks i różni się od oryginału
    assert enc != original
    assert enc.startswith("enc::")
    assert su.decrypt(enc) == original


def test_encrypt_empty_passthrough():
    assert su.encrypt("") == ""
    assert su.encrypt(None) is None
    assert su.decrypt("") == ""
    assert su.decrypt(None) is None


def test_decrypt_plaintext_passthrough():
    # wartości bez prefiksu (np. starsze, niezaszyfrowane) zwracane bez zmian
    assert su.decrypt("plain-old-value") == "plain-old-value"


def test_double_encrypt_is_idempotent():
    enc = su.encrypt("token")
    # ponowne szyfrowanie już-zaszyfrowanej wartości nie nakłada drugiej warstwy
    assert su.encrypt(enc) == enc


def test_is_encryption_active_returns_bool():
    assert isinstance(su.is_encryption_active(), bool)


def test_encrypt_handles_missing_fernet(monkeypatch):
    # symulujemy brak klucza -> degradacja: zwraca tekst bez zmian
    monkeypatch.setattr(su, "_get_fernet", lambda: None)
    assert su.encrypt("token") == "token"
    assert su.decrypt("enc::whatever") == "enc::whatever"
