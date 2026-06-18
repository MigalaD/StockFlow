"""
Testy dla tickers.py
=====================
Walidują format symboli w listach skanera - jedna literówka (spacja, mała
litera, brak sufiksu .WA/-USD) powoduje "błąd" dla pozycji, która powinna
działać, więc lepiej wyłapać to testem niż przy demie.
"""
import re

import tickers

_SYMBOL = re.compile(r"^[A-Z0-9.\-^]+$")

_ALL_LISTS = {
    "SKANER_USA": tickers.SKANER_USA,
    "SKANER_GPW": tickers.SKANER_GPW,
    "SKANER_EUROPA": tickers.SKANER_EUROPA,
    "SKANER_KRYPTO": tickers.SKANER_KRYPTO,
    "SKANER_ETF": tickers.SKANER_ETF,
    "SKANER_KOMODITY": tickers.SKANER_KOMODITY,
}


def test_all_symbols_have_valid_format():
    for name, lst in _ALL_LISTS.items():
        for t in lst:
            assert isinstance(t, str) and t, f"{name}: pusty symbol {t!r}"
            assert _SYMBOL.match(t), f"{name}: zły format {t!r}"
            assert t == t.strip(), f"{name}: białe znaki w {t!r}"


def test_no_duplicates_within_lists():
    for name, lst in _ALL_LISTS.items():
        assert len(lst) == len(set(lst)), f"{name}: zawiera duplikaty"


def test_gpw_symbols_have_wa_suffix():
    for t in tickers.SKANER_GPW:
        assert t.endswith(".WA"), f"GPW bez .WA: {t!r}"


def test_crypto_symbols_have_usd_suffix():
    for t in tickers.SKANER_KRYPTO:
        assert t.endswith("-USD"), f"Krypto bez -USD: {t!r}"


def test_wszystkie_is_union_of_regions():
    expected = len(tickers.SKANER_USA) + len(tickers.SKANER_GPW) + len(tickers.SKANER_EUROPA)
    assert len(tickers.SKANER_WSZYSTKIE) == expected
