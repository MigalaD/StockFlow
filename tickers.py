"""
Listy spółek
=============
Centralna lista tickerów używana przez dashboard (lista przykładowa),
skaner rynku i sekcję "Spółki wzrostowe". Edytuj swobodnie - dodawaj
i usuwaj symbole.

Symbole spoza USA mają sufiksy giełd wymagane przez yfinance:
- GPW (Warszawa):    .WA   np. CDR.WA
- Niemcy (XETRA):    .DE   np. SAP.DE
- Wielka Brytania:   .L    np. AZN.L
- Francja (Euronext): .PA  np. MC.PA
"""

# ----------------------------------------------------------------------
# Spółki pokazywane w dropdownie dashboardu (nazwa wyświetlana -> ticker)
# ----------------------------------------------------------------------
PRZYKLADOWE_SPOLKI = {
    # USA - technologia / duże spółki
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "Tesla (TSLA)": "TSLA",
    "Nvidia (NVDA)": "NVDA",
    "Amazon (AMZN)": "AMZN",
    "Google (GOOGL)": "GOOGL",
    "Meta (META)": "META",
    "Netflix (NFLX)": "NFLX",
    "Berkshire Hathaway (BRK-B)": "BRK-B",
    "JPMorgan Chase (JPM)": "JPM",
    "Johnson & Johnson (JNJ)": "JNJ",
    "Visa (V)": "V",
    # GPW - WIG20 + popularne
    "CD Projekt (CDR.WA)": "CDR.WA",
    "PKO BP (PKO.WA)": "PKO.WA",
    "Allegro (ALE.WA)": "ALE.WA",
    "PKN Orlen (PKN.WA)": "PKN.WA",
    "KGHM (KGH.WA)": "KGH.WA",
    "PZU (PZU.WA)": "PZU.WA",
    "Pepco (PCO.WA)": "PCO.WA",
    "Dino Polska (DNP.WA)": "DNP.WA",
    "LPP (LPP.WA)": "LPP.WA",
    # Niemcy (DAX)
    "SAP (SAP.DE)": "SAP.DE",
    "Siemens (SIE.DE)": "SIE.DE",
    "Volkswagen (VOW3.DE)": "VOW3.DE",
    "Allianz (ALV.DE)": "ALV.DE",
    # Wielka Brytania (FTSE)
    "AstraZeneca (AZN.L)": "AZN.L",
    "Shell (SHEL.L)": "SHEL.L",
    "HSBC (HSBA.L)": "HSBA.L",
    # Francja (CAC40)
    "LVMH (MC.PA)": "MC.PA",
    "TotalEnergies (TTE.PA)": "TTE.PA",
    # ETF-y i surowce (przykłady)
    "S&P 500 ETF (SPY)": "SPY",
    "Nasdaq 100 ETF (QQQ)": "QQQ",
    "Złoto ETF (GLD)": "GLD",
}

# ----------------------------------------------------------------------
# Tickery do skanera rynku - podzielone wg rynków
# ----------------------------------------------------------------------

# USA - próbka (nie cały S&P 500, żeby skan trwał rozsądnie)
SKANER_USA = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX",
    "AMD", "INTC", "CRM", "ADBE", "ORCL", "CSCO", "QCOM", "AVGO", "IBM",
    "JPM", "BAC", "WFC", "GS", "V", "MA", "AXP", "BRK-B",
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "LLY", "TMO",
    "XOM", "CVX", "COP", "SLB",
    "WMT", "COST", "PG", "KO", "PEP", "MCD", "TGT",
    "DIS", "NKE", "SBUX", "HD", "LOW",
    "BA", "CAT", "GE", "HON", "UPS",
]

# GPW (Warszawa) - WIG20 + kilka popularnych spoza
SKANER_GPW = [
    "PKN.WA", "PKO.WA", "PEO.WA", "PZU.WA", "KGH.WA", "CDR.WA",
    "ALE.WA", "DNP.WA", "LPP.WA", "CPS.WA", "PCO.WA", "SPL.WA",
    "MBK.WA", "BHW.WA", "OPL.WA", "TPE.WA", "PGE.WA", "JSW.WA",
    "KRU.WA", "ALR.WA", "CCC.WA", "ZAB.WA", "BDX.WA", "KTY.WA",
]

# Europa Zachodnia - Niemcy (DAX), UK (FTSE), Francja (CAC40), Holandia
SKANER_EUROPA = [
    # Niemcy
    "SAP.DE", "SIE.DE", "VOW3.DE", "ALV.DE", "BAS.DE", "BMW.DE",
    "DTE.DE", "MBG.DE", "ADS.DE", "MUV2.DE",
    # Wielka Brytania
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "GSK.L",
    "DGE.L", "RIO.L", "BATS.L", "VOD.L",
    # Francja
    "MC.PA", "TTE.PA", "OR.PA", "SAN.PA", "AIR.PA", "BNP.PA",
    "AI.PA", "SU.PA",
    # Holandia
    "ASML.AS", "ADYEN.AS",
    # Szwajcaria
    "NESN.SW", "NOVN.SW", "ROG.SW",
]

# Pełna lista użyta przez skaner ("Wszystko")
SKANER_WSZYSTKIE = SKANER_USA + SKANER_GPW + SKANER_EUROPA


# ----------------------------------------------------------------------
# "Spółki wzrostowe" - sekcja dla osób szukających ciekawych, mniejszych
# lub niedawno wprowadzonych na giełdę spółek do śledzenia.
#
# WAŻNE: to NIE są prywatne startupy (te nie mają publicznych danych
# finansowych - Yahoo Finance ich nie obsługuje, a dostęp do takich danych
# wymaga płatnych baz typu Crunchbase/PitchBook). To spółki już PUBLICZNE
# (po IPO), często młode, o wyższym ryzyku i wyższej zmienności niż duże,
# ugruntowane firmy - dlatego warto je "śledzić", ale z większą ostrożnością.
#
# Format: nazwa wyświetlana -> (ticker, krótki opis "czemu warto śledzić")
# ----------------------------------------------------------------------
SPOLKI_WZROSTOWE = {
    "Reddit (RDDT)": ("RDDT", "Niedawne IPO (2024) - platforma social media z rosnącymi przychodami z reklam i danych do AI."),
    "Arm Holdings (ARM)": ("ARM", "Projektant architektur procesorów - kluczowy dla rynku mobile i coraz bardziej AI/chipów."),
    "Astera Labs (ALAB)": ("ALAB", "Chipy do połączeń w centrach danych AI - mała spółka, duża ekspozycja na boom AI."),
    "CrowdStrike (CRWD)": ("CRWD", "Cyberbezpieczeństwo w modelu SaaS - szybko rosnące przychody, wysoka wycena."),
    "Snowflake (SNOW)": ("SNOW", "Platforma danych w chmurze - silny wzrost przychodów, wciąż niska/ brak rentowności."),
    "Palantir (PLTR)": ("PLTR", "Analiza danych dla rządu i biznesu - duża zmienność, silny sentyment AI."),
    "Affirm (AFRM)": ("AFRM", "Fintech BNPL (buy now pay later) - wzrostowa, ale wrażliwa na stopy procentowe."),
    "Klaviyo (KVYO)": ("KVYO", "Marketing/CRM dla e-commerce - niedawne IPO, rosnąca baza klientów."),
    "Allegro (ALE.WA)": ("ALE.WA", "Największy polski e-commerce - po debiucie giełdowym, ekspansja regionalna."),
    "Pepco Group (PCO.WA)": ("PCO.WA", "Szybko rosnąca sieć dyskontowa w Europie - ekspansja w wielu krajach."),
}


# ----------------------------------------------------------------------
# ETF-y - fundusze notowane na giełdzie (akcje funduszu, śledzą indeks/koszyk
# aktywów). Score dla ETF-ów wyklucza wskaźniki fundamentalne spółek
# (P/E, dywidenda spółki, dług/wzrost) - patrz stock_analyzer.get_asset_type.
#
# Format: nazwa wyświetlana -> (ticker, krótki opis co śledzi)
# ----------------------------------------------------------------------
ETF_LIST = {
    "S&P 500 (SPY)": ("SPY", "Największe 500 spółek USA - 'rynek' w pigułce."),
    "Nasdaq 100 (QQQ)": ("QQQ", "100 największych spółek technologicznych/growth z Nasdaq."),
    "Total US Market (VTI)": ("VTI", "Cały rynek akcji USA (duże, średnie i małe spółki)."),
    "Rynki rozwinięte ex-US (EFA)": ("EFA", "Akcje dużych spółek z Europy, Australii i Dalekiego Wschodu."),
    "Rynki wschodzące (VWO)": ("VWO", "Akcje spółek z rynków wschodzących (Chiny, Indie, Brazylia, itd.)."),
    "Innowacje/ARK (ARKK)": ("ARKK", "Aktywnie zarządzany ETF spółek 'disruptive innovation' - bardzo zmienny."),
    "Sektor technologiczny (XLK)": ("XLK", "Spółki technologiczne z S&P 500."),
    "Sektor energetyczny (XLE)": ("XLE", "Spółki z sektora energetycznego (ropa, gaz) z S&P 500."),
    "Sektor finansowy (XLF)": ("XLF", "Banki i instytucje finansowe z S&P 500."),
    "Nieruchomości / REIT (VNQ)": ("VNQ", "Fundusze nieruchomości (REIT) - alternatywa do posiadania nieruchomości."),
    "Obligacje długoterminowe (TLT)": ("TLT", "Długoterminowe obligacje rządu USA - zwykle przeciwwaga do akcji."),
    "WIG20 (ETFW20L.WA)": ("ETFW20L.WA", "ETF na indeks WIG20 (20 największych spółek GPW)."),
}

# Tickery ETF do skanera rynku
SKANER_ETF = [
    "SPY", "QQQ", "VTI", "VOO", "IWM", "EFA", "VWO", "ARKK",
    "XLK", "XLE", "XLF", "XLV", "XLI", "XLY", "XLP", "XLU",
    "VNQ", "TLT", "IEF", "HYG",
]


# ----------------------------------------------------------------------
# SUROWCE - tu używamy ETF-ów towarowych (śledzą cenę surowca, są płynne
# i mają stabilną historię w yfinance) zamiast kontraktów futures (=F),
# które bywają mniej stabilne pod względem dostępności danych.
#
# Score dla surowców wyklucza WSZYSTKIE wskaźniki fundamentalne
# (P/E, dywidenda, fundamenty spółki) - surowce ich z definicji nie mają.
# Liczy się tylko analiza techniczna (trend, RSI, MACD, zmienność,
# momentum) + sentyment newsów.
#
# Format: nazwa wyświetlana -> (ticker, krótki opis)
# ----------------------------------------------------------------------
KOMODITY_LIST = {
    "Złoto (GLD)": ("GLD", "ETF śledzący cenę złota - klasyczna 'bezpieczna przystań' w czasach niepewności."),
    "Srebro (SLV)": ("SLV", "ETF śledzący cenę srebra - bardziej zmienny niż złoto, ma też zastosowania przemysłowe."),
    "Ropa WTI (USO)": ("USO", "ETF śledzący cenę ropy WTI - silnie powiązany z globalną koniunkturą."),
    "Gaz ziemny (UNG)": ("UNG", "ETF śledzący cenę gazu ziemnego - bardzo wysoka zmienność, sezonowość."),
    "Koszyk surowców (DBC)": ("DBC", "Zdywersyfikowany koszyk surowców (energia, metale, rolnictwo)."),
    "Miedź (CPER)": ("CPER", "ETF śledzący cenę miedzi - czasem nazywana 'Dr Copper', barometr koniunktury przemysłowej."),
    "Rolnictwo (DBA)": ("DBA", "Koszyk surowców rolnych (zboża, soja, cukier, kawa itd.)."),
}

# Tickery surowcowe do skanera rynku
SKANER_KOMODITY = ["GLD", "SLV", "USO", "UNG", "DBC", "CPER", "DBA"]


# ----------------------------------------------------------------------
# KRYPTO - popularne kryptowaluty dostępne przez Yahoo Finance
# (format: TICKER-USD). Traktowane jak "commodity" w stock_analyzer –
# analiza czysto techniczna (trend, RSI, MACD, zmienność, momentum).
# ----------------------------------------------------------------------
KRYPTO_LIST = {
    "Bitcoin (BTC)":    ("BTC-USD", "Największa kryptowaluta wg kapitalizacji. Często traktowana jak 'cyfrowe złoto'."),
    "Ethereum (ETH)":   ("ETH-USD", "Platforma smart-kontraktów – 'fundament' ekosystemu DeFi i NFT."),
    "Solana (SOL)":     ("SOL-USD", "Szybki blockchain o niskich opłatach – rywal Ethereum w obszarze smart-kontraktów."),
    "BNB (BNB)":        ("BNB-USD", "Token giełdy Binance – jeden z największych tokenów utility."),
    "XRP (XRP)":        ("XRP-USD", "Sieć płatności międzybankowych Ripple – duża zmienność, historycznie spory."),
    "Cardano (ADA)":    ("ADA-USD", "Blockchain oparty na dowodach akademickich (proof-of-stake, Haskell)."),
    "Avalanche (AVAX)": ("AVAX-USD", "Platforma smart-kontraktów z naciskiem na prędkość i ekosystem DeFi."),
    "Polkadot (DOT)":   ("DOT-USD", "Protokół interoperacyjności – łączy różne blockchainy."),
}

SKANER_KRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                  "ADA-USD", "AVAX-USD", "DOT-USD"]
