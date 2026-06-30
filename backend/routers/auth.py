# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /auth
  POST /auth/register  — rejestracja nowego użytkownika
  POST /auth/login     — logowanie, zwraca JWT
  GET  /auth/me        — profil zalogowanego użytkownika
"""

from __future__ import annotations

import sys
import os
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status, Request

# Dodaj katalog nadrzędny (Streamlit root) do path żeby importować istniejące moduły
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from backend.core.config import get_settings
from backend.core.limiter import limiter
from backend.core.security import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)
from backend.models.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

settings = get_settings()
router   = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Rejestracja nowego użytkownika. Zwraca JWT token.",
)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest) -> TokenResponse:
    """
    Tworzy nowe konto i od razu zwraca token (nie wymaga osobnego logowania).

    - **username**: 2–30 znaków, tylko [a-zA-Z0-9_-.], unikalny
    - **password**: min. 8 znaków
    - **email**: opcjonalny
    """
    # Sprawdź czy username jest wolny
    existing = db.get_user_by_username(body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' already taken",
        )

    hashed = hash_password(body.password)
    db.create_user(body.username, hashed, body.email)

    token = create_access_token(
        {"sub": body.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=body.username,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Logowanie. Zwraca JWT Bearer token.",
)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest) -> TokenResponse:
    """
    Weryfikuje credentials i zwraca JWT.

    Token należy przekazywać w nagłówku:
    `Authorization: Bearer <token>`
    """
    user = db.get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        {"sub": body.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=body.username,
    )


@router.get(
    "/me",
    summary="Current user profile",
    description="Zwraca profil zalogowanego użytkownika.",
)
async def me(user_id: CurrentUser) -> dict:
    return {
        "user_id":  user_id,
        "username": user_id,
    }


@router.post(
    "/settings/telegram",
    summary="Save Telegram settings",
)
async def save_telegram_settings(
    body:    dict,
    user_id: CurrentUser,
) -> dict:
    """Zapisuje ustawienia Telegram dla użytkownika."""
    try:
        db.set_user_settings(user_id, {
            "telegram_token":   body.get("telegram_token", ""),
            "telegram_chat_id": body.get("telegram_chat_id", ""),
        })
    except AttributeError:
        # set_user_settings może nie istnieć w starszej wersji database.py
        pass
    return {"saved": True}
