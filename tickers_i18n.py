# Copyright (c) 2026 Damian Migała / StockFlow

"""
Angielskie opisy instrumentów — Etap 3 i18n.

DLACZEGO OSOBNY PLIK, A NIE ZMIANA STRUKTURY W tickers.py:
opisy w tickers.py siedzą w krotkach ("TICKER", "opis"), które konsumuje
kilka routerów (etf, commodities, growth). Zmiana na {"pl":..., "en":...}
wymagałaby przerobienia każdego miejsca użycia i zwiększała ryzyko błędu
na produkcji. Tutaj nakładamy tłumaczenie po tickerze: brak wpisu =
automatyczny fallback na polski opis, więc nic nie może się zepsuć.

Użycie w routerze:
    from tickers_i18n import describe
    opis_lokalny = describe(ticker, opis, lang)
"""

from __future__ import annotations

DESCRIPTIONS_EN: dict[str, str] = {
    # ── ETF ──
    "SPY":  "The 500 largest US companies - the 'market' in a nutshell.",
    "QQQ":  "The 100 largest technology/growth companies on Nasdaq.",
    "VTI":  "The entire US equity market (large, mid and small caps).",
    "EFA":  "Large-cap equities from Europe, Australia and the Far East.",
    "VWO":  "Equities from emerging markets (China, India, Brazil and others).",
    "ARKK": "Actively managed ETF of 'disruptive innovation' companies - highly volatile.",
    "XLK":  "Technology companies from the S&P 500.",
    "XLE":  "Energy sector companies (oil, gas) from the S&P 500.",
    "XLF":  "Banks and financial institutions from the S&P 500.",
    "VNQ":  "Real estate investment trusts (REITs) - an alternative to owning property.",
    "TLT":  "Long-term US government bonds - typically a counterweight to equities.",
    "ETFW20L.WA": "ETF tracking the WIG20 index (20 largest companies on the Warsaw Stock Exchange).",
    "VWCE.DE": "The whole world in a single ETF (accumulating) - the most popular choice among Polish investors. UCITS.",
    "SXR8.DE": "S&P 500 in its European version (accumulating). UCITS - available in the EU.",
    "IWDA.AS": "Developed markets worldwide (accumulating). UCITS - available in the EU.",
    "EUNL.DE": "MSCI World listed on Xetra in EUR (accumulating). UCITS - available in the EU.",
    "VUSA.AS": "S&P 500 paying out dividends, listed in Amsterdam. UCITS - available in the EU.",

    # ── Surowce ──
    "GLD":  "ETF tracking the price of gold - the classic 'safe haven' in uncertain times.",
    "SLV":  "ETF tracking the price of silver - more volatile than gold, with industrial uses too.",
    "USO":  "ETF tracking WTI crude oil - closely tied to the global business cycle.",
    "UNG":  "ETF tracking natural gas - very high volatility and strong seasonality.",
    "DBC":  "A diversified basket of commodities (energy, metals, agriculture).",
    "CPER": "ETF tracking copper - sometimes called 'Dr Copper', a barometer of industrial activity.",
    "DBA":  "A basket of agricultural commodities (grains, soy, sugar, coffee and others).",
    "PPLT": "ETF tracking platinum - a precious metal with industrial uses (catalytic converters).",
    "PALL": "ETF tracking palladium - critical for the automotive industry, with highly concentrated supply.",
    "WEAT": "ETF on wheat futures - sensitive to weather and geopolitics.",
    "CORN": "ETF on corn futures - a cornerstone of the agricultural market.",

    # ── Krypto ──
    "BTC-USD":  "The largest cryptocurrency by market capitalisation. Often treated as 'digital gold'.",
    "ETH-USD":  "A smart-contract platform - the foundation of the DeFi and NFT ecosystem.",
    "SOL-USD":  "A fast, low-fee blockchain - a rival to Ethereum in smart contracts.",
    "BNB-USD":  "The Binance exchange token - one of the largest utility tokens.",
    "XRP-USD":  "Ripple's interbank payment network - high volatility, a history of legal disputes.",
    "ADA-USD":  "A blockchain built on peer-reviewed academic research (proof-of-stake, Haskell).",
    "AVAX-USD": "A smart-contract platform focused on speed and the DeFi ecosystem.",
    "DOT-USD":  "An interoperability protocol - connects different blockchains.",
    "DOGE-USD": "Originally a joke, now one of the largest 'meme coins' - extreme volatility.",
    "LINK-USD": "An oracle network - feeds real-world data into smart contracts.",
    "LTC-USD":  "One of the oldest cryptocurrencies - the 'silver' to Bitcoin's gold.",
    "ATOM-USD": "An ecosystem of connected blockchains (the 'internet of blockchains').",
    "UNI-USD":  "The token of the largest decentralised exchange (DEX) on Ethereum.",
    "TRX-USD":  "A blockchain geared towards cheap transactions and stablecoins - popular in Asia.",
    "NEAR-USD": "An efficient L1 blockchain with an emphasis on developer simplicity.",
    "SHIB-USD": "The second-largest 'meme coin' - highly speculative.",

    # ── Spółki wzrostowe ──
    "ARM":  "Designer of processor architectures - central to mobile and increasingly to AI chips.",
    "ALAB": "Chips for data-centre interconnects in AI - a small company with large AI exposure.",
    "PLTR": "Data analytics for government and business - high volatility, strong AI sentiment.",
    "SMCI": "Servers and infrastructure for AI - rapid growth, high volatility.",
    "MRVL": "Semiconductors for data centres and infrastructure - exposure to AI.",
    "CRWD": "Cybersecurity delivered as SaaS - fast-growing revenue, rich valuation.",
    "ZS":   "Cloud-based network security (zero-trust) - a growing market.",
    "SNOW": "A cloud data platform - strong revenue growth, low profitability.",
    "DDOG": "Monitoring for applications and cloud infrastructure - steady growth.",
    "NET":  "Internet infrastructure and security - broad exposure to web traffic.",
    "KVYO": "Marketing/CRM for e-commerce - a recent IPO with a growing customer base.",
    "RDDT": "A recent IPO (2024) - social media with growing revenue from ads and AI data licensing.",
    "AFRM": "BNPL fintech (buy now, pay later) - growth-oriented, sensitive to interest rates.",
    "XYZ":  "Fintech (Square, Cash App) - payments and a broader financial ecosystem.",
    "SHOP": "An e-commerce platform for merchants - the leader in its segment.",
    "ALE.WA": "Poland's largest e-commerce marketplace - expanding across the region.",
    "PCO.WA": "A fast-growing discount retail chain in Europe - expanding across many countries.",
    "TXT.WA": "Polish SaaS (formerly LiveChat) - customer service software with high margins.",
    "XTB.WA": "Broker/fintech - rapid growth in its retail client base.",
    "DNP.WA": "A supermarket chain - consistent, rapid growth in store count.",
}


def describe(ticker: str, fallback_pl: str, lang: str = "pl") -> str:
    """Zwraca opis instrumentu w danym języku.

    Fallback: brak tłumaczenia -> polski opis z tickers.py. Dzięki temu
    dodanie nowego instrumentu nigdy nie wywoła pustego opisu, nawet jeśli
    ktoś zapomni dopisać tłumaczenie."""
    if lang == "en":
        return DESCRIPTIONS_EN.get(ticker.upper(), fallback_pl)
    return fallback_pl
