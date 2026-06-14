"""
Security utilities — JWT, password hashing, T8 hardening.

Provides:
  - hash_password / verify_password (bcrypt)
  - create_access_token / create_refresh_token / decode_token
  - SecurityHeadersMiddleware: HSTS, CSP, X-Frame-Options, etc.
  - configure_rate_limiter: per-IP/per-user throttling
  - require_strong_secret / validate_secrets_at_startup
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("clientfinder.security")

# --- Password hashing (bcrypt) ---
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12
)


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


# --- JWT helpers ---
def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=15)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.app_secret, algorithm="HS256")


def create_refresh_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token (longer expiry)."""
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.app_secret, algorithm="HS256")


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any] | None:
    """Decode and validate a JWT. Returns payload dict or None if invalid."""
    try:
        payload = jwt.decode(token, settings.app_secret, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


# --- T8: Secret validation ---
DEFAULT_SECRETS = {
    "change-me",
    "changeme",
    "secret",
    "password",
    "admin",
    "",
    "your-secret-key",
    "your-secret",
    "your-jwt-secret",
    "your-groq-api-key",
    "your-gemini-api-key",
    "your-tokenrouter-key",
    "PLACEHOLDER_REPLACE_WITH_GROQ_KEY",
    "PLACEHOLDER_REPLACE_WITH_GEMINI_KEY",
    "PLACEHOLDER_REPLACE_WITH_TOKENROUTER_KEY",
}

MIN_SECRET_LENGTHS = {
    "APP_SECRET": 32,
    "SMTP_PASSWORD": 8,
    "WAHA_API_KEY": 8,
}


def require_strong_secret(name: str, value: str | None) -> None:
    """Raise if a secret is missing, default, or too short.

    In `app_env=local`, missing/default are allowed (dev convenience).
    In any other env, they're fatal.
    """
    if settings.app_env == "local":
        if not value or value.lower() in DEFAULT_SECRETS:
            logger.warning(
                "Secret %s is missing or default. OK for local dev, "
                "MUST be set for staging/prod.",
                name,
            )
        return

    if not value:
        raise RuntimeError(
            f"Secret {name} is required (app_env={settings.app_env}). "
            f"Set it in .env before booting."
        )
    if value.lower() in DEFAULT_SECRETS:
        raise RuntimeError(
            f"Secret {name} has a default/placeholder value. "
            f"Generate a real one before booting in {settings.app_env}."
        )
    min_len = MIN_SECRET_LENGTHS.get(name, 16)
    if len(value) < min_len:
        raise RuntimeError(
            f"Secret {name} is too short ({len(value)} < {min_len}). "
            f"Use a longer value."
        )


def validate_secrets_at_startup() -> None:
    """Run all required-secret checks at app boot."""
    require_strong_secret("APP_SECRET", settings.app_secret)
    if settings.smtp_user:
        require_strong_secret("SMTP_PASSWORD", settings.smtp_password or None)
    if settings.waha_api_key:
        require_strong_secret("WAHA_API_KEY", settings.waha_api_key)
    if settings.app_env != "local" and settings.app_debug:
        raise RuntimeError(
            f"APP_DEBUG must be false in {settings.app_env}. "
            f"Set APP_DEBUG=false in .env."
        )
    logger.info("All required secrets validated.")


# --- T8: Security headers middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds world-class security headers to every response.

    - HSTS: enforce HTTPS for 1 year (incl. subdomains)
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (anti-clickjacking)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: deny camera, mic, geolocation, payment
    - Content-Security-Policy: strict default-src 'self'
    - Cross-Origin-Opener-Policy: same-origin
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        if request.url.path in ("/docs", "/redoc", "/openapi.json"):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'"
            )
        else:
            csp = "default-src 'self'; frame-ancestors 'none'"
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if "server" in response.headers:
            del response.headers["server"]
        return response


# --- T8: Rate limiter ---
def _client_key(request: Request) -> str:
    """Per-IP for unauthenticated, per-user for authenticated.

    Hashes the token (first 16 chars of SHA-256) so we don't
    leak any PII into the rate limit storage.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            h = hashlib.sha256(token.encode()).hexdigest()[:16]
            return f"user:{h}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_client_key,
    default_limits=["200/minute"],
    storage_uri="memory://",  # v1 in-memory; use redis in prod
    strategy="fixed-window",
)


def configure_rate_limiter(app: FastAPI) -> None:
    """Attach the limiter + exception handler to the app."""
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,
    )


async def _rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> Response:
    logger.warning(
        "Rate limit exceeded on %s %s: %s",
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMITED",
                "message": f"Too many requests. Limit: {exc.detail}",
            },
        },
        headers={"Retry-After": "60"},
    )
