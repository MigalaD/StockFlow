# Copyright (c) 2026 Damian Migała / StockFlow
# Wszystkie prawa zastrzeżone. All rights reserved.

"""
Konfiguracja aplikacji FastAPI.
Zmienne środowiskowe ładowane z .env (python-dotenv) lub z systemu.

Zmienne wymagane w produkcji:
  DATABASE_URL   — PostgreSQL URL (Supabase): postgresql://user:pass@host/db
  SECRET_KEY     — klucz JWT (min. 32 znaki, generuj: openssl rand -hex 32)
  ALLOWED_ORIGINS — CORS origins oddzielone przecinkiem

Zmienne opcjonalne:
  ALPACA_API_KEY / ALPACA_SECRET_KEY — live quotes dla akcji USA
  ENCRYPTION_KEY — Fernet key (kompatybilność z istniejącą bazą SQLite)
  DB_PATH        — ścieżka do SQLite (fallback gdy brak DATABASE_URL)
  ENVIRONMENT    — "development" | "production" (default: development)
  LOG_LEVEL      — "DEBUG" | "INFO" | "WARNING" (default: INFO)
"""

from __future__ import annotations
import os
from functools import lru_cache
from typing import Literal

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv opcjonalne w dev


class Settings:
    # ── Środowisko ───────────────────────────────────────────────────
    environment: Literal["development", "production"] = os.getenv(
        "ENVIRONMENT", "development"
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # ── Baza danych ──────────────────────────────────────────────────
    # Supabase/PostgreSQL w produkcji, SQLite jako fallback w dev
    database_url: str | None = os.getenv("DATABASE_URL")
    db_path: str = os.getenv("DB_PATH", "./stock_app.db")

    @property
    def use_postgres(self) -> bool:
        return self.database_url is not None

    # ── Bezpieczeństwo ───────────────────────────────────────────────
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production-min32chars")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")  # 24h
    )

    # ── CORS ─────────────────────────────────────────────────────────
    # W dev: allow all. W produkcji: ustaw ALLOWED_ORIGINS
    allowed_origins_str: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8501"
    )

    @property
    def allowed_origins(self) -> list[str]:
        if self.environment == "development":
            return ["*"]
        return [o.strip() for o in self.allowed_origins_str.split(",") if o.strip()]

    # ── API zewnętrzne ────────────────────────────────────────────────
    alpaca_api_key: str | None = os.getenv("ALPACA_API_KEY")
    alpaca_secret_key: str | None = os.getenv("ALPACA_SECRET_KEY")

    # ── Cache ────────────────────────────────────────────────────────
    # TTL dla cache'owania wyników analyze_ticker (sekundy)
    analysis_cache_ttl: int = int(os.getenv("ANALYSIS_CACHE_TTL", "900"))
    scan_cache_ttl: int    = int(os.getenv("SCAN_CACHE_TTL", "3600"))

    # ── Rate limiting ─────────────────────────────────────────────────
    yf_rate_limit: int = int(os.getenv("YF_RATE_LIMIT", "4"))

    # ── Wersja ────────────────────────────────────────────────────────
    app_version: str = "1.1.0"
    app_name: str    = "StockFlow API"


@lru_cache
def get_settings() -> Settings:
    return Settings()
