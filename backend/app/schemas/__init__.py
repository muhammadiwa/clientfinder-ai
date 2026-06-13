"""
Pydantic schemas for API request/response
"""
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, Token
from app.schemas.prospect import (
    ProspectCreate,
    ProspectListResponse,
    ProspectOut,
    ProspectUpdate,
)
from app.schemas.scraping import (
    ScrapingJobCreate,
    ScrapingJobListResponse,
    ScrapingJobOut,
    ScrapingPresetOut,
)
from app.schemas.user import UserCreate, UserInDB, UserOut, UserUpdate

__all__ = [
    "LoginRequest",
    "LogoutRequest",
    "RefreshRequest",
    "Token",
    "UserCreate",
    "UserInDB",
    "UserOut",
    "UserUpdate",
    "ProspectCreate",
    "ProspectListResponse",
    "ProspectOut",
    "ProspectUpdate",
    "ScrapingJobCreate",
    "ScrapingJobListResponse",
    "ScrapingJobOut",
    "ScrapingPresetOut",
]