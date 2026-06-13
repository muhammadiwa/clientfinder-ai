"""
Application Configuration (Pydantic Settings)
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "ClientFinder"
    app_version: str = "0.1.0"
    app_env: str = "local"
    app_debug: bool = True
    app_secret: str = "change-me"
    app_timezone: str = "Asia/Jakarta"
    app_base_url: str = "http://localhost"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.backend_cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    # Database
    database_url: str = "postgresql+asyncpg://clientfinder:clientfinder@localhost:5432/clientfinder"

    # Redis
    redis_url: str = "redis://:password@localhost:6379/0"
    redis_max_connections: int = 20

    # Celery
    celery_broker_url: str = "redis://:password@localhost:6379/1"
    celery_result_backend: str = "redis://:password@localhost:6379/2"
    celery_worker_concurrency: int = 2
    celery_task_time_limit: int = 600
    celery_task_soft_time_limit: int = 540

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "clientfinder"
    minio_secret_key: str = "change-me"
    minio_bucket_prospects: str = "prospects"
    minio_bucket_screenshots: str = "screenshots"
    minio_bucket_raw: str = "raw-data"
    minio_use_ssl: bool = False

    # SearXNG
    searxng_base_url: str = "http://localhost:8888"
    searxng_secret: str = "change-me"

    # LLM
    llm_primary_provider: str = "groq"
    llm_primary_model: str = "llama-3.1-70b-versatile"
    llm_primary_api_key: str = ""
    llm_fallback_provider: str = "gemini"
    llm_fallback_model: str = "gemini-1.5-flash"
    llm_fallback_api_key: str = ""
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048

    # Email
    smtp_host: str = "smtp.zoho.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "ClientFinder"
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    smtp_daily_limit: int = 100

    # WhatsApp
    waha_base_url: str = "http://waha:3000"
    waha_session_name: str = "default"
    waha_api_key: str = ""

    # Threads
    threads_cookies_path: str = "/app/.sessions/threads_cookies.json"
    threads_daily_dm_limit: int = 20

    # Scraping
    scraper_user_agent_rotation: bool = True
    scraper_request_delay_min: int = 3
    scraper_request_delay_max: int = 8
    scraper_max_concurrent: int = 2
    scraper_proxy_enabled: bool = False

    # Outreach
    outreach_auto_approve: bool = False
    outreach_business_hours_start: str = "09:00"
    outreach_business_hours_end: str = "18:00"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
