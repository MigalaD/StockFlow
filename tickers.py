# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

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
    # Rozszerzenie: półprzewodniki/software, finanse, zdrowie, przemysł, telko
    "TXN", "AMAT", "MU", "NOW", "UBER", "ABNB", "PYPL",
    "MS", "C", "SCHW", "GILD", "AMGN", "BMY",
    "LMT", "RTX", "DE", "T", "VZ",
]

# GPW (Warszawa) - WIG20 + kilka popularnych spoza
SKANER_GPW = [
    "PKN.WA", "PKO.WA", "PEO.WA", "PZU.WA", "KGH.WA", "CDR.WA",
    "ALE.WA", "DNP.WA", "LPP.WA", "CPS.WA", "PCO.WA", "SPL.WA",
    "MBK.WA", "BHW.WA", "OPL.WA", "TPE.WA", "PGE.WA", "JSW.WA",
    "KRU.WA", "ALR.WA", "CCC.WA", "ZAB.WA", "BDX.WA", "KTY.WA",
    # Rozszerzenie: banki, przemysł, tech/gaming, energetyka
    "ATT.WA", "GPW.WA", "ENA.WA", "XTB.WA", "TXT.WA", "NEU.WA",
    "MIL.WA", "ING.WA", "11B.WA", "ASE.WA", "LWB.WA", "EAT.WA",
]

# Spółki dywidendowe GPW — kandydaci do panelu "Dywidendy".
# Kuratorowana lista spółek znanych z regularnych wypłat. Nie każda
# musi płacić co roku — panel sam wykryje status z historii wypłat
# (spółki bez dywidend dostają status "nie wypłaca", nie błąd).
SPOLKI_DYWIDENDOWE_GPW = [
    "PKO.WA", "PZU.WA", "PEO.WA", "PKN.WA", "KGH.WA", "SPL.WA",
    "KTY.WA", "ACP.WA", "LPP.WA", "WPL.WA", "OPL.WA", "PGE.WA",
    "MBK.WA", "BHW.WA", "ALR.WA", "KRU.WA", "GPW.WA", "ATT.WA",
    "TPE.WA", "ENA.WA", "CPS.WA", "ASE.WA", "NEU.WA", "BDX.WA",
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
    # Rozszerzenie: Niemcy, Włochy, Hiszpania, Finlandia
    "IFX.DE", "BAYN.DE", "DHL.DE",
    "ENEL.MI", "ENI.MI", "ISP.MI",
    "IBE.MC", "ITX.MC", "SAN.MC",
    "NOKIA.HE",
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
    # ── AI / Półprzewodniki ──
    "Arm Holdings (ARM)": ("ARM", "Projektant architektur procesorów - kluczowy dla mobile i coraz bardziej AI/chipów."),
    "Astera Labs (ALAB)": ("ALAB", "Chipy do połączeń w centrach danych AI - mała spółka, duża ekspozycja na boom AI."),
    "Palantir (PLTR)": ("PLTR", "Analiza danych dla rządu i biznesu - duża zmienność, silny sentyment AI."),
    "Super Micro (SMCI)": ("SMCI", "Serwery i infrastruktura pod AI - gwałtowny wzrost, wysoka zmienność."),
    "Marvell (MRVL)": ("MRVL", "Półprzewodniki do centrów danych i infrastruktury - ekspozycja na AI."),
    # ── Cyberbezpieczeństwo ──
    "CrowdStrike (CRWD)": ("CRWD", "Cyberbezpieczeństwo w modelu SaaS - szybko rosnące przychody, wysoka wycena."),
    "Zscaler (ZS)": ("ZS", "Bezpieczeństwo sieci w chmurze (zero-trust) - rosnący rynek."),
    # ── Chmura / Dane / SaaS ──
    "Snowflake (SNOW)": ("SNOW", "Platforma danych w chmurze - silny wzrost przychodów, niska rentowność."),
    "Datadog (DDOG)": ("DDOG", "Monitoring aplikacji i infrastruktury chmurowej - stały wzrost."),
    "Cloudflare (NET)": ("NET", "Infrastruktura i bezpieczeństwo internetu - szeroka ekspozycja na ruch sieciowy."),
    "Klaviyo (KVYO)": ("KVYO", "Marketing/CRM dla e-commerce - niedawne IPO, rosnąca baza klientów."),
    # ── Fintech / Internet ──
    "Reddit (RDDT)": ("RDDT", "Niedawne IPO (2024) - social media z rosnącymi przychodami z reklam i danych do AI."),
    "Affirm (AFRM)": ("AFRM", "Fintech BNPL (buy now pay later) - wzrostowa, wrażliwa na stopy procentowe."),
    "Block (XYZ)": ("XYZ", "Fintech (Square, Cash App) - płatności i ekosystem finansowy."),
    "Shopify (SHOP)": ("SHOP", "Platforma e-commerce dla sprzedawców - lider w swoim segmencie."),
    # ── Polskie wzrostowe (GPW) ──
    "Allegro (ALE.WA)": ("ALE.WA", "Największy polski e-commerce - ekspansja regionalna."),
    "Pepco Group (PCO.WA)": ("PCO.WA", "Szybko rosnąca sieć dyskontowa w Europie - ekspansja w wielu krajach."),
    "Text (TXT.WA)": ("TXT.WA", "Polski SaaS (dawniej LiveChat) - oprogramowanie do obsługi klienta, wysokie marże."),
    "XTB (XTB.WA)": ("XTB.WA", "Broker/fintech - dynamiczny wzrost bazy klientów detalicznych."),
    "Dino Polska (DNP.WA)": ("DNP.WA", "Sieć supermarketów - konsekwentny, szybki wzrost liczby sklepów."),
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
    # ── UCITS — wersje europejskie, DOSTĘPNE dla polskich inwestorów ──
    # (amerykańskich ETF-ów jak SPY/QQQ polski inwestor detaliczny zwykle
    #  nie kupi przez PRIIPs/KID — te poniżej TAK, przez polskich brokerów)
    "Vanguard All-World UCITS (VWCE.DE)": ("VWCE.DE", "Cały świat w jednym ETF (akumulujący) - najpopularniejszy wybór polskich inwestorów. UCITS."),
    "iShares Core S&P 500 UCITS (SXR8.DE)": ("SXR8.DE", "S&P 500 w wersji europejskiej (akumulujący). UCITS - dostępny w PL."),
    "iShares MSCI World UCITS (IWDA.AS)": ("IWDA.AS", "Rynki rozwinięte całego świata (akumulujący). UCITS - dostępny w PL."),
    "iShares Core MSCI World (EUNL.DE)": ("EUNL.DE", "MSCI World na Xetra w EUR (akumulujący). UCITS - dostępny w PL."),
    "Vanguard S&P 500 dist. (VUSA.AS)": ("VUSA.AS", "S&P 500 z wypłatą dywidend, Amsterdam. UCITS - dostępny w PL."),
}

# Tickery ETF do skanera rynku
SKANER_ETF = [
    "SPY", "QQQ", "VTI", "VOO", "IWM", "EFA", "VWO", "ARKK",
    "XLK", "XLE", "XLF", "XLV", "XLI", "XLY", "XLP", "XLU",
    "VNQ", "TLT", "IEF", "HYG",
    "VWCE.DE", "SXR8.DE", "IWDA.AS", "EUNL.DE", "VUSA.AS",
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
    "Platyna (PPLT)": ("PPLT", "ETF śledzący cenę platyny - metal szlachetny o zastosowaniach przemysłowych (katalizatory)."),
    "Pallad (PALL)": ("PALL", "ETF śledzący cenę palladu - kluczowy w motoryzacji, mocno skoncentrowana podaż."),
    "Pszenica (WEAT)": ("WEAT", "ETF na kontrakty pszenicy - wrażliwy na pogodę i geopolitykę."),
    "Kukurydza (CORN)": ("CORN", "ETF na kontrakty kukurydzy - fundament rynku rolnego."),
}

# Tickery surowcowe do skanera rynku
SKANER_KOMODITY = ["GLD", "SLV", "USO", "UNG", "DBC", "CPER", "DBA",
                    "PPLT", "PALL", "WEAT", "CORN"]


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
    "Dogecoin (DOGE)":  ("DOGE-USD", "Pierwotnie żart, dziś jedna z największych 'meme coins' – ekstremalna zmienność."),
    "Chainlink (LINK)": ("LINK-USD", "Sieć wyroczni (oracle) – dostarcza dane ze świata rzeczywistego do smart-kontraktów."),
    "Litecoin (LTC)":   ("LTC-USD", "Jedna z najstarszych kryptowalut – 'srebro' wobec złota Bitcoina."),
    "Cosmos (ATOM)":    ("ATOM-USD", "Ekosystem połączonych blockchainów ('internet of blockchains')."),
    "Uniswap (UNI)":    ("UNI-USD", "Token największej zdecentralizowanej giełdy (DEX) na Ethereum."),
    "TRON (TRX)":       ("TRX-USD", "Blockchain nastawiony na tanie transakcje i stablecoiny – popularny w Azji."),
    "NEAR (NEAR)":      ("NEAR-USD", "Wydajny blockchain L1 z naciskiem na prostotę dla developerów."),
    "Shiba Inu (SHIB)": ("SHIB-USD", "Druga największa 'meme coin' – bardzo spekulacyjna."),
}

SKANER_KRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                  "ADA-USD", "AVAX-USD", "DOT-USD",
                  "DOGE-USD", "LINK-USD", "LTC-USD", "ATOM-USD",
                  "UNI-USD", "TRX-USD", "NEAR-USD", "SHIB-USD"]
