# ClientFinder AI Agent

> AI-powered lead generation agent for freelance software developers.
> Temukan UMKM Indonesia yang butuh jasa digital — scoring otomatis, outreach personal.

[![Phase](https://img.shields.io/badge/phase-T1-blue)]() [![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20PostgreSQL-green)]() [![License](https://img.shields.io/badge/license-MIT-yellow)]()

## What is this?

ClientFinder adalah **AI agent** yang:

1. **SCOUT** — Cari bisnis yang punya indikasi butuh software (Google, Maps, Twitter, Threads)
2. **ANALYZE** — Audit kebutuhan mereka, deteksi pain points, skor lead
3. **OUTREACH** — Generate pesan personal, kirim via Email/WhatsApp/Threads
4. **TRACK** — Simpan ke CRM, follow-up otomatis dengan human approval

Fokus: **UMKM Indonesia** (klinik, F&B, retail, jasa, manufaktur kecil).

## Architecture

```
React (Vite)  →  Nginx (reverse proxy)
                     │
                     ├──► FastAPI (backend API)
                     │       │
                     │       ├──► PostgreSQL  (data)
                     │       ├──► Redis       (cache + queue)
                     │       └──► MinIO       (files)
                     │
                     ├──► Celery Worker (scraping/analysis/outreach tasks)
                     ├──► Celery Beat   (scheduler)
                     ├──► Flower        (worker monitor)
                     ├──► SearXNG       (Google search proxy)
                     └──► WAHA          (WhatsApp gateway)
```

## Quick Start (Local)

### Prerequisites
- Docker 24+ & Docker Compose v2
- 4 GB+ RAM, 10 GB+ disk
- Linux/macOS/WSL2

### Setup

```bash
# 1. Clone & enter project
cd /home/kumaha-sia/clientfinder

# 2. Copy & edit env
cp .env.example .env
nano .env   # set strong passwords (see below)

# 3. Generate strong secrets
export POSTGRES_PASSWORD=$(openssl rand -hex 24)
export REDIS_PASSWORD=$(openssl rand -hex 24)
export MINIO_ROOT_PASSWORD=$(openssl rand -hex 24)
export APP_SECRET=$(openssl rand -hex 32)
export SEARXNG_SECRET=$(openssl rand -hex 24)
# replace placeholders in .env with these values

# 4. Build & start
make build
make up

# 5. Check health
make health

# 6. Open in browser
# Frontend:  http://localhost
# Backend:   http://localhost/api/v1
# API docs:  http://localhost/docs
# Flower:    http://localhost:5555
# MinIO:     http://localhost:9001
# SearXNG:   http://localhost:8888
```

### Common Commands

```bash
make help             # list all available commands
make up               # start all services
make down             # stop all services
make logs             # tail all logs
make backend-shell    # open shell in backend container
make postgres-shell   # open psql
make redis-shell      # open redis-cli
make migrate          # run DB migrations
make test             # run tests
make lint             # run linting
make health           # check service status
```

## Project Structure

```
clientfinder/
├── backend/           # FastAPI + Celery
├── frontend/          # React + Vite + TypeScript
├── ops/               # Infrastructure configs
│   ├── nginx/         # Reverse proxy
│   ├── searxng/       # Search engine
│   ├── postgres/      # DB init
│   ├── minio/         # Object storage
│   └── waha/          # WhatsApp API (T6)
├── docs/              # Documentation
├── scripts/           # Helper scripts
├── docker-compose.yml # Main compose file
├── Makefile           # Common commands
└── .env.example       # Environment template
```

## Development Roadmap

| Phase | Status | Deliverable |
|---|---|---|
| **T1** | ✅ Done | Infrastructure foundation (this phase) |
| **T2** | ⏳ Next | Backend core: DB, auth, models |
| **T3** | Pending | Frontend core: routing, auth, layout |
| **T4** | Pending | Scout module: 4 scrapers |
| **T5** | Pending | Analyst module: audit, scoring, LLM |
| **T6** | Pending | Outreach module: email, WA, threads |
| **T7** | Pending | Analytics & lead pipeline |
| **T8** | Pending | Production hardening |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full technical design.

## Tech Stack

**Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.0 · Celery · Playwright · twikit
**Frontend:** React 18 · TypeScript · Vite · TanStack Query · shadcn/ui · Tailwind
**Data:** PostgreSQL 16 · Redis 7 · MinIO · SearXNG
**AI:** Groq (Llama 3.1 70B) + Gemini 1.5 Flash (free tier)
**Infra:** Docker · Nginx · Caddy (prod)

All **free & open source**. Total operational cost: VPS only (~$10-25/mo).

## License

MIT © Juragan
