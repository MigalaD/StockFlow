# Copyright (c) 2026 Damian Migała / StockFlow

"""
i18n backendu — tłumaczenie treści MERYTORYCZNYCH generowanych po stronie
serwera (notatki score, flagi, ostrzeżenia, opisy).

DLACZEGO TUTAJ, A NIE TYLKO WE FRONCIE:
część tekstów powstaje w Pythonie i trafia w dwa miejsca — na ekran ORAZ
do raportu PDF (generowanego serwerowo). Gdyby składać zdania we froncie,
PDF wymagałby drugiego, równoległego słownika. Tutaj logika jest jedna.

UŻYCIE:
    from i18n import t
    t("rsi.oversold", lang, value=45.2, threshold=30)

ZASADA BEZPIECZEŃSTWA: brak klucza lub brak tłumaczenia NIGDY nie wywala
odpowiedzi — wraca wersja polska (fallback), a w skrajnym przypadku sam
klucz. Dzięki temu tłumaczenia można dodawać przyrostowo, funkcja po
funkcji, bez ryzyka, że pominięte miejsce zepsuje produkcję.
"""

from __future__ import annotations

import logging

log = logging.getLogger("stockflow.i18n")

DEFAULT_LANG = "pl"
SUPPORTED_LANGS = ("pl", "en")


def normalize_lang(raw: str | None) -> str:
    """Normalizuje wartość nagłówka Accept-Language do obsługiwanego kodu.

    Akceptuje 'en', 'en-US', 'en-US,en;q=0.9,pl;q=0.8' itd.
    Nieznany/pusty język -> DEFAULT_LANG (polski)."""
    if not raw:
        return DEFAULT_LANG
    # Weź pierwszy język z listy preferencji i obetnij region oraz wagę q
    first = raw.split(",")[0].split(";")[0].strip().lower()
    primary = first.split("-")[0]
    return primary if primary in SUPPORTED_LANGS else DEFAULT_LANG


# ──────────────────────────────────────────────────────────────────────
# SŁOWNIK
#
# Konwencja kluczy: "<obszar>.<konkret>", np. "rsi.oversold".
# Wartości mogą zawierać pola {nazwa} wypełniane przez t(..., nazwa=...).
# ──────────────────────────────────────────────────────────────────────

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Ogólne / brak danych ──
    "common.no_data": {
        "pl": "brak danych",
        "en": "no data",
    },
    "common.unknown": {
        "pl": "Nieznany",
        "en": "Unknown",
    },

    # ── Typy aktywów (sektor zastępczy) ──
    "asset.crypto": {
        "pl": "Kryptowaluta",
        "en": "Cryptocurrency",
    },
    "asset.commodity": {
        "pl": "Surowiec / kontrakt",
        "en": "Commodity / futures",
    },
    "asset.etf": {
        "pl": "ETF",
        "en": "ETF",
    },

    # ── RSI ──
    "rsi.no_data": {
        "pl": "brak danych RSI",
        "en": "no RSI data",
    },
    "rsi.oversold": {
        "pl": "RSI={value:.1f} (wyprzedanie, próg {threshold:.0f}{note})",
        "en": "RSI={value:.1f} (oversold, threshold {threshold:.0f}{note})",
    },
    "rsi.overbought": {
        "pl": "RSI={value:.1f} (przegrzanie, próg {threshold:.0f}{note})",
        "en": "RSI={value:.1f} (overbought, threshold {threshold:.0f}{note})",
    },
    "rsi.neutral": {
        "pl": "RSI={value:.1f} (neutralnie{note})",
        "en": "RSI={value:.1f} (neutral{note})",
    },
    "rsi.thresholds_wide": {
        "pl": ", progi poszerzone (wysoka zmienność)",
        "en": ", thresholds widened (high volatility)",
    },
    "rsi.thresholds_narrow": {
        "pl": ", progi zawężone (niska zmienność)",
        "en": ", thresholds narrowed (low volatility)",
    },

    # ── Wycena (relatywna do sektora) ──
    "valuation.no_pe": {
        "pl": "brak danych P/E (możliwe straty / brak danych)",
        "en": "no P/E data (possible losses / missing data)",
    },
    "valuation.sector_median": {
        "pl": "mediana sektora ~{median:.0f}",
        "en": "sector median ~{median:.0f}",
    },
    "valuation.much_cheaper": {
        "pl": "wyraźnie taniej niż {ref}",
        "en": "notably cheaper than {ref}",
    },
    "valuation.cheaper": {
        "pl": "taniej niż {ref}",
        "en": "cheaper than {ref}",
    },
    "valuation.in_line": {
        "pl": "wycena zbliżona do {ref_gen}",
        "en": "valuation in line with {ref_gen}",
    },
    "valuation.pricier": {
        "pl": "drożej niż {ref}",
        "en": "pricier than {ref}",
    },
    "valuation.much_pricier": {
        "pl": "wyraźnie drożej niż {ref}",
        "en": "notably pricier than {ref}",
    },
    "valuation.ref_sector": {"pl": "sektor", "en": "sector"},
    "valuation.ref_market": {"pl": "rynek", "en": "the market"},
    "valuation.ref_sector_gen": {"pl": "sektora", "en": "the sector"},
    "valuation.ref_market_gen": {"pl": "rynku", "en": "the market"},
    "valuation.low_pe": {"pl": "niskie P/E", "en": "low P/E"},
    "valuation.high_pe": {"pl": "wysokie P/E", "en": "high P/E"},
    "valuation.forward_better": {
        "pl": "forward P/E={fpe:.1f} (oczekiwany wzrost zysków)",
        "en": "forward P/E={fpe:.1f} (earnings growth expected)",
    },
    "valuation.forward_worse": {
        "pl": "forward P/E={fpe:.1f} (oczekiwany spadek zysków)",
        "en": "forward P/E={fpe:.1f} (earnings decline expected)",
    },

    # ── Trend / średnie kroczące ──
    "trend.no_ma200": {
        "pl": "brak danych do MA200",
        "en": "insufficient data for MA200",
    },
    "trend.above_ma50": {"pl": "cena > MA50", "en": "price > MA50"},
    "trend.below_ma50": {"pl": "cena < MA50", "en": "price < MA50"},
    "trend.above_ma200": {"pl": "cena > MA200", "en": "price > MA200"},
    "trend.below_ma200": {"pl": "cena < MA200", "en": "price < MA200"},
    "trend.golden_cross": {
        "pl": "złoty krzyż (MA50>MA200)",
        "en": "golden cross (MA50>MA200)",
    },
    "trend.death_cross": {
        "pl": "krzyż śmierci (MA50<MA200)",
        "en": "death cross (MA50<MA200)",
    },

    # ── Wolumen ──
    "volume.normal": {
        "pl": "wolumen normalny ({ratio:.1f}x średniej)",
        "en": "normal volume ({ratio:.1f}x average)",
    },
    "volume.high": {
        "pl": "wolumen podwyższony ({ratio:.1f}x średniej)",
        "en": "elevated volume ({ratio:.1f}x average)",
    },
    "volume.low": {
        "pl": "wolumen niski ({ratio:.1f}x średniej)",
        "en": "low volume ({ratio:.1f}x average)",
    },

    # ── Dywidendy: profil i flagi ──
    "div.not_paying": {
        "pl": "Spółka nie wypłaca dywidendy",
        "en": "Company does not pay a dividend",
    },
    "div.never_cut": {
        "pl": "Dywidenda nigdy nie obcięta",
        "en": "Dividend never cut",
    },
    "div.cut_deep": {
        "pl": "W przeszłości cięcie dywidendy o {pct:.0%}",
        "en": "Past dividend cut of {pct:.0%}",
    },
    "div.cut_mild": {
        "pl": "Dywidenda bywała obniżana (max -{pct:.0%})",
        "en": "Dividend has been reduced before (max -{pct:.0%})",
    },
    "div.rising": {"pl": "Rosnąca dywidenda", "en": "Rising dividend"},
    "div.falling": {"pl": "Malejąca dywidenda", "en": "Declining dividend"},
    "div.streak": {
        "pl": "{years} lat nieprzerwanych wypłat",
        "en": "{years} consecutive years of payouts",
    },
    "div.payout_uncovered": {
        "pl": "Dywidenda niepokryta zyskiem (payout >100%)",
        "en": "Dividend not covered by earnings (payout >100%)",
    },
    "div.payout_high": {"pl": "Wysoki payout ratio", "en": "High payout ratio"},
    "div.payout_healthy": {"pl": "Zdrowy payout ratio", "en": "Healthy payout ratio"},
    "div.yield_very_high": {
        "pl": "Bardzo wysoka stopa — sprawdź trwałość",
        "en": "Very high yield — verify sustainability",
    },
    "div.yield_extreme": {
        "pl": "Ekstremalnie wysoka stopa — ryzyko cięcia",
        "en": "Extremely high yield — risk of a cut",
    },
    "div.profile_solid": {
        "pl": "Solidny profil dywidendowy",
        "en": "Solid dividend profile",
    },
    "div.profile_decent": {
        "pl": "Przyzwoity profil dywidendowy",
        "en": "Decent dividend profile",
    },
    "div.profile_concerns": {
        "pl": "Profil dywidendowy z zastrzeżeniami",
        "en": "Dividend profile with caveats",
    },
    "div.long_history": {
        "pl": "długa historia wypłat",
        "en": "long payout history",
    },
    "div.desc_rising": {"pl": "dywidenda rośnie", "en": "dividend is growing"},
    "div.desc_falling": {"pl": "dywidenda maleje", "en": "dividend is shrinking"},

    # ── Portfel: ostrzeżenia ──
    "portfolio.fx_failed": {
        "pl": "⚠️ Nie udało się pobrać kursów walut dla części pozycji — łączna wartość może być niedokładna.",
        "en": "⚠️ Could not fetch exchange rates for some positions — total value may be inaccurate.",
    },
    "portfolio.concentration_position": {
        "pl": "⚠️ {ticker} stanowi {share:.0%} portfela - jedna spółka ma duży wpływ na cały wynik.",
        "en": "⚠️ {ticker} accounts for {share:.0%} of the portfolio - a single holding heavily drives the result.",
    },
    "portfolio.concentration_sector": {
        "pl": "⚠️ Sektor '{sector}' stanowi {pct:.0f}% portfela - słaba dywersyfikacja branżowa.",
        "en": "⚠️ Sector '{sector}' accounts for {pct:.0f}% of the portfolio - weak sector diversification.",
    },
    "portfolio.single_position": {
        "pl": "⚠️ Portfel składa się z jednej spółki - brak dywersyfikacji.",
        "en": "⚠️ The portfolio holds a single position - no diversification.",
    },

    # ── PDF: etykiety raportu ──
    "pdf.title": {"pl": "Raport analizy", "en": "Analysis report"},
    "pdf.generated": {"pl": "Wygenerowano", "en": "Generated"},
    "pdf.score_long": {"pl": "Score długoterminowy", "en": "Long-term score"},
    "pdf.score_short": {"pl": "Score krótkoterminowy", "en": "Short-term score"},
    "pdf.components": {"pl": "Składowe oceny", "en": "Score components"},
    "pdf.component": {"pl": "Składowa", "en": "Component"},
    "pdf.value": {"pl": "Ocena", "en": "Score"},
    "pdf.comment": {"pl": "Komentarz", "en": "Comment"},
    "pdf.red_flags": {"pl": "Sygnały ostrzegawcze", "en": "Warning signals"},
    "pdf.price": {"pl": "Cena", "en": "Price"},
    "pdf.sector": {"pl": "Sektor", "en": "Sector"},
    "pdf.positive": {"pl": "Pozytywny", "en": "Positive"},
    "pdf.neutral": {"pl": "Neutralny", "en": "Neutral"},
    "pdf.negative": {"pl": "Negatywny", "en": "Negative"},
    "pdf.disclaimer": {
        "pl": "Raport ma charakter edukacyjny i informacyjny. Nie stanowi rekomendacji inwestycyjnej. "
              "Decyzje inwestycyjne podejmujesz na własną odpowiedzialność.",
        "en": "This report is for educational and informational purposes only. It is not investment advice. "
              "You make investment decisions at your own risk.",
    },
    "pdf.data_coverage": {"pl": "Pokrycie danych", "en": "Data coverage"},
    "pdf.report_header": {"pl": "Raport analizy", "en": "Analysis report"},
    "pdf.sector_price": {
        "pl": "Sektor: {sector}  ·  Cena: {price:.2f} {currency}",
        "en": "Sector: {sector}  ·  Price: {price:.2f} {currency}",
    },
    "pdf.components_dt": {"pl": "Składowe wyniku DT", "en": "Long-term score components"},
    "pdf.col_indicator": {"pl": "Wskaźnik", "en": "Indicator"},
    "pdf.col_result": {"pl": "Wynik", "en": "Result"},
    "pdf.col_weight": {"pl": "Waga", "en": "Weight"},
    "pdf.col_signal": {"pl": "Sygnał", "en": "Signal"},
    "pdf.red_flags_header": {"pl": "Ostrzeżenia (Red Flags)", "en": "Warnings (Red Flags)"},
    "pdf.footer_tagline": {
        "pl": "StockFlow  ·  Narzędzie edukacyjne  ·  Nie stanowi porady inwestycyjnej",
        "en": "StockFlow  ·  Educational tool  ·  Not investment advice",
    },
    "pdf.generated_at": {"pl": "Wygenerowano: {now}", "en": "Generated: {now}"},
    "pdf.score_dt": {"pl": "Score DT", "en": "Long-term score"},
    "pdf.score_st": {"pl": "Score ST", "en": "Short-term score"},
}


def t(key: str, lang: str = DEFAULT_LANG, **params) -> str:
    """Zwraca przetłumaczony tekst dla klucza.

    Fallback jest wielopoziomowy i CELOWO nigdy nie rzuca wyjątku:
      brak języka -> polski,
      brak klucza  -> sam klucz (widoczny sygnał do uzupełnienia, ale
                      nie wywraca odpowiedzi API),
      zły parametr -> tekst bez podstawienia.
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        log.warning("i18n: brak klucza '%s'", key)
        return key

    template = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError) as e:
        log.warning("i18n: błąd podstawienia dla '%s': %s", key, e)
        return template
