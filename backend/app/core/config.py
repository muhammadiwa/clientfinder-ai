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

    # LLM (legacy simple 2-slot config — backward compatible)
    llm_primary_provider: str = "groq"
    llm_primary_base_url: str | None = None  # for custom OAI-compatible
    llm_primary_model: str = "llama-3.1-70b-versatile"
    llm_primary_api_key: str = ""
    llm_fallback_provider: str = "gemini"
    llm_fallback_base_url: str | None = None
    llm_fallback_model: str = "gemini-1.5-flash"
    llm_fallback_api_key: str = ""
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048

    # LLM (advanced — JSON list of providers, full control)
    # When set, OVERRIDES the simple primary+fallback config.
    # Each entry: {name, type, base_url, api_key, model, enabled, order, display_name}
    #   - name: unique id (e.g. "groq", "tokenrouter", "ollama")
    #   - type: "openai-compatible" or "gemini"
    #   - base_url: required for OAI-compatible (auto-filled for known names)
    #   - api_key: any string (use "ollama" for local)
    #   - model: model identifier
    #   - enabled: true/false (toggle on/off without removing)
    #   - order: 1=primary, 2=fallback, 3+=chain
    # Example:
    #   LLM_PROVIDERS_JSON='[
    #     {"name":"tokenrouter","type":"openai-compatible",
    #      "api_key":"sk-...","model":"MiniMax-M3",
    #      "enabled":true,"order":1,"display_name":"TokenRouter"},
    #     {"name":"groq","type":"openai-compatible",
    #      "api_key":"gsk-...","model":"llama-3.1-70b-versatile",
    #      "enabled":true,"order":2},
    #     {"name":"ollama","type":"openai-compatible",
    #      "base_url":"http://host.docker.internal:11434/v1",
    #      "api_key":"ollama","model":"llama3",
    #      "enabled":false,"order":3}
    #   ]'
    llm_providers_json: str = ""

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

    # T9.0 — Social Signal Agent scrapers (Twitter / Threads)
    # Both scrapers use cookie-based auth per R7 pragmatic-legal.
    # Cookies are NOT committed (gitignored) — the operator must
    # upload them manually via the setup script.
    twitter_cookies_path: str = "/app/.sessions/twitter_cookies.json"
    twitter_search_max_per_query: int = 30
    twitter_max_age_days: int = 14
    # When True, falls back to "no signals this run" if cookies are
    # missing or stale instead of raising. Default True = pipeline
    # stays healthy when cookies aren't set up yet.
    twitter_soft_fail: bool = True

    # Scraping
    scraper_user_agent_rotation: bool = True
    scraper_request_delay_min: int = 3
    scraper_request_delay_max: int = 8
    scraper_max_concurrent: int = 2
    scraper_proxy_enabled: bool = False

    # Sprint 1 / Phase 1.1 — Google Search kill switch
    # (DEPRECATED 2026-06-14: the noisy SearXNG-backed Google source
    # was removed from the scout flow. Kept here as a stub for
    # migration history. The prefilter.py utility was also removed.)
    scout_google_enabled: bool = False
    scout_google_prefilter_enabled: bool = True
    scout_google_max_results_per_query: int = 50  # cap before prefilter

    # DEPRECATED 2026-06-14: 3C source kill switches
    # (Google Places, Yelp, Tokopedia). Kept as stubs for re-enable.
    # To re-enable, restore the matching field in `_SCRAPERS`
    # (backend/app/services/scraper/__init__.py) and the SOURCES array
    # in frontend/src/pages/Scout.tsx.
    google_places_api_key: str = ""
    scout_google_places_enabled: bool = False
    scout_google_places_max_per_query: int = 30

    yelp_api_key: str = ""
    scout_yelp_enabled: bool = False
    scout_yelp_max_per_query: int = 30

    # Sprint 3C sub-task 2 — Tokopedia seller search (Playwright)
    scout_tokopedia_enabled: bool = False
    scout_tokopedia_max_per_query: int = 20
    scout_tokopedia_headless: bool = True
    scout_tokopedia_page_timeout_s: int = 20

    # Scout enrichment (T8.6) — homepage fetch for phone/email/address/socials
    scout_enrichment_enabled: bool = True
    scout_enrichment_page_timeout_s: int = 12
    scout_enrichment_overall_timeout_s: int = 240
    scout_enrichment_max_concurrent: int = 1
    # Sprint 4 / PR 1 followup: auto-enrich hook (per-prospect
    # website audit + scoring) was removed in PR 115 but the
    # wiring in scraping_tasks._run_job was still auto-firing
    # enrich_prospect_task.delay() for every new prospect. This
    # kill switch controls the auto-fire path. v1 = False
    # (opt-in via the per-prospect "Enrich" button in the UI).
    # Aligns with the user spec: "hapus dulu proses enrich
    # otomatis kita ulang dari awal lagi".
    scout_auto_enrich_enabled: bool = False

    # Outreach
    outreach_auto_approve: bool = False
    outreach_business_hours_start: str = "09:00"
    outreach_business_hours_end: str = "18:00"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
