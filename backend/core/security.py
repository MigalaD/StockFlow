# Copyright (c) 2026 Damian Migała / StockFlow

"""
Uwierzytelnianie JWT.

Funkcje:
  create_access_token(data)  — generuje token JWT
  verify_token(token)        — weryfikuje token, zwraca payload lub None
  get_current_user(token)    — FastAPI dependency, zwraca user_id
  get_optional_user(token)   — jak wyżej, ale nie failuje gdy brak tokenu
  hash_password(pw)          — bcrypt hash
  verify_password(pw, hash)  — weryfikacja hasła
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from jose import JWTError, jwt
except ImportError:
    raise RuntimeError("Zainstaluj: pip install python-jose[cryptography]")

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    raise RuntimeError("Zainstaluj: pip install passlib[bcrypt]")

from .config import get_settings

settings = get_settings()
_bearer  = HTTPBearer(auto_error=False)


# ── Hasła ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Tworzy podpisany token JWT z payloadem `data`."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> dict | None:
    """Weryfikuje token JWT. Zwraca payload lub None przy błędzie."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


# ── FastAPI dependencies ───────────────────────────────────────────────

def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ] = None,
) -> str:
    """
    FastAPI dependency — wymagane uwierzytelnienie.
    Zwraca user_id z tokenu JWT.
    Rzuca 401 gdy brak lub nieprawidłowy token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user ID",
        )
    return user_id


def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ] = None,
) -> str | None:
    """
    FastAPI dependency — opcjonalne uwierzytelnienie.
    Zwraca user_id lub None gdy brak tokenu.
    Używane dla endpointów dostępnych publicznie (np. /analyze).
    """
    if not credentials:
        return None
    payload = verify_token(credentials.credentials)
    if not payload:
        return None
    return payload.get("sub")


# Type aliases dla użycia w routerach
CurrentUser         = Annotated[str,        Depends(get_current_user)]
OptionalCurrentUser = Annotated[str | None, Depends(get_optional_user)]
