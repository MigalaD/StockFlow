# Copyright (c) 2026 Damian Migała / StockFlow

"""
Pydantic modele — walidacja requestów i serializacja odpowiedzi API.

Konwencja nazewnictwa:
  *Request  — payload przychodzący (body POST/PUT)
  *Response — odpowiedź API
  *Item     — element listy
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    password: str = Field(..., min_length=8, max_length=128)
    email:    str | None = Field(None, max_length=255)

    model_config = {"json_schema_extra": {"example": {
        "username": "damian", "password": "haslo1234", "email": "damian@example.com"
    }}}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int   # sekundy
    user_id:      str


# ── Analiza ────────────────────────────────────────────────────────────

class ComponentItem(BaseModel):
    key:   str
    score: float
    note:  str
    weight: float


class AnalysisResponse(BaseModel):
    ticker:       str
    name:         str
    price:        float
    currency:     str
    total_score:  float
    score_st:     float | None
    asset_type:   str
    sector:       str | None
    industry:     str | None
    components:   list[ComponentItem]
    components_st: list[ComponentItem]
    red_flags:    list[str]
    vwap:         dict[str, Any] | None
    ma_crossover: dict[str, Any] | None
    beta_info:    dict[str, Any] | None
    relative_strength: dict[str, Any] | None
    cached_at:    str | None = None


class ScoreHistoryItem(BaseModel):
    date:  str
    score: float


# ── Watchlist ──────────────────────────────────────────────────────────

class WatchlistAddRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()


class WatchlistAlertRequest(BaseModel):
    alert_high:       float | None = Field(None, ge=0, le=100)
    alert_low:        float | None = Field(None, ge=0, le=100)
    alert_crossover:  bool = False


class WatchlistItem(BaseModel):
    ticker:           str
    last_score:       float | None
    alert_high:       float | None
    alert_low:        float | None
    alert_crossover:  bool
    added_at:         str | None


# ── Portfolio ──────────────────────────────────────────────────────────

class PositionAddRequest(BaseModel):
    ticker:    str = Field(..., min_length=1, max_length=20)
    shares:    float = Field(..., gt=0)
    buy_price: float = Field(..., gt=0)
    buy_date:  str | None = None
    notes:     str | None = Field(None, max_length=500)

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()


class PositionItem(BaseModel):
    id:            int
    ticker:        str
    name:          str
    shares:        float
    buy_price:     float
    current_price: float
    current_value: float
    pnl:           float
    pnl_pct:       float
    currency:      str
    sector:        str
    buy_date:      str | None
    notes:         str | None
    score:         float | None


class PortfolioResponse(BaseModel):
    positions:           list[PositionItem]
    total_value:         float
    total_pnl:           float
    total_pnl_pct:       float
    allocation_by_sector: dict[str, float]
    warnings:            list[str]


# ── Dziennik ──────────────────────────────────────────────────────────

class JournalAddRequest(BaseModel):
    entry_date: str
    ticker:     str = Field(..., min_length=1, max_length=20)
    decision:   str
    reason:     str = Field(..., max_length=2000)
    score:      float | None = None
    price:      float | None = None

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()


class JournalItem(BaseModel):
    id:         int
    entry_date: str
    ticker:     str
    decision:   str
    reason:     str
    score:      float | None
    price:      float | None
    created_at: str | None


# ── Skaner ────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    market: str = Field(
        "usa",
        description="Rynek do skanowania: usa | gpw | europa | krypto | all",
    )

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: str) -> str:
        allowed = {"usa", "gpw", "europa", "krypto", "all"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Market must be one of: {allowed}")
        return v


class ScanResultItem(BaseModel):
    ticker:   str
    name:     str | None
    sector:   str | None
    price:    float | None
    score:    float
    score_st: float | None


class ScanResponse(BaseModel):
    results:    list[ScanResultItem]
    scanned_at: str
    total:      int


# ── Dane rynkowe ──────────────────────────────────────────────────────

class OHLCVItem(BaseModel):
    timestamp: str
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float


class MarketDataResponse(BaseModel):
    ticker:   str
    interval: str
    source:   str
    candles:  list[OHLCVItem]


# ── Health / Info ─────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:  str
    version: str
    db:      str
    sources: dict[str, str]


class InfoResponse(BaseModel):
    name:    str
    version: str
    docs:    str
    langs:   list[str]
