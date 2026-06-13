# Architecture

Dokumentasi ini menjelaskan arsitektur teknikal ClientFinder AI Agent secara lengkap.

## High-Level Overview

ClientFinder adalah sistem multi-layer yang terdiri dari:

1. **Frontend (React SPA)** — Dashboard untuk manage prospects, leads, outreach
2. **Backend API (FastAPI)** — REST API + WebSocket untuk real-time updates
3. **Workers (Celery)** — Async task execution (scraping, analysis, outreach)
4. **Data layer (Postgres + Redis + MinIO)** — Persistent storage
5. **External services (SearXNG, WAHA, SMTP, Threads)** — Third-party integrations

## Module Breakdown

### SCOUT Module
Tujuan: cari prospek baru dari berbagai sumber.

| Source | Method | Status |
|---|---|---|
| Google Search | SearXNG meta-search | T4 |
| Google Maps | Playwright scraper | T4 |
| Twitter | twikit library | T4 |
| Threads | Playwright + cookies | T4 |

### ANALYST Module
Tujuan: ubah raw prospect data jadi lead score + outreach hooks.

| Component | Method | Status |
|---|---|---|
| Tech Audit | Playwright + custom heuristics | T5 |
| Pain Detection | LLM (Groq/Gemini) | T5 |
| Lead Scoring | Formula + LLM reasoning | T5 |
| Hook Generation | LLM with prompt template | T5 |

### OUTREACH Module
Tujuan: kirim pesan personal via multi-channel.

| Channel | Method | Status |
|---|---|---|
| Email | SMTP (Postfix/Zoho) | T6 |
| WhatsApp | WAHA HTTP API | T6 |
| Threads DM | Playwright automation | T6 |

## Database Schema

Lihat [ARCHITECTURE.md §4](README.md#database-schema-core-tables) di blueprint awal untuk ERD lengkap.

Inti tabel:
- `users` — auth
- `prospects` — master data bisnis
- `signals` — evidence per prospek
- `tech_stacks` — hasil audit
- `pain_points` — masalah teridentifikasi
- `lead_scores` — skor & reasoning
- `hooks` — personalization angle
- `messages` — outreach (draft → sent → replied)
- `sequences` — multi-step campaign
- `templates` — reusable message templates
- `activities` — audit log
- `settings` — key-value config
- `scraping_jobs` — job tracking

## Security Model

- JWT auth (httpOnly cookies, 15min access + 7d refresh)
- bcrypt password hashing
- RBAC: owner / admin / member
- 2FA (TOTP) untuk owner
- Rate limiting (Nginx + slowapi)
- HTTPS only (production)
- Secrets in env vars, never in code
- Audit log semua mutation
- Database backup terenkripsi

## Deployment Topology

**Local dev:** semua service di `docker compose`, port 80/443 via nginx container.

**Production:** identik dengan local, tambahan:
- Domain + DNS pointing
- Let's Encrypt SSL cert (auto-renew via certbot atau Caddy)
- Monitoring (Prometheus + Grafana)
- Backup automation (pg_dump + GPG → offsite)
- Log aggregation (Loki)
- Optional: CDN (Cloudflare) untuk DDoS protection

## Data Flow Example: New Prospect

```
1. User creates scraping job via /scraping/jobs (POST)
   └─► Job disimpan di DB, status=pending

2. Celery beat picks up job, dispatches ke worker
   └─► Worker calls SearXNG → Google → parse HTML
   └─► Untuk setiap result, simpan ke prospects table
   └─► Status berubah: running → completed

3. Post-scrape hook fires: enrich_prospect(prospect_id)
   └─► Tech audit: Playwright visit website, detect CMS/framework
   └─► Pain detection: LLM analyze review/posts
   └─► Scoring: formula compute + LLM reasoning
   └─► Hook generation: LLM generate 2-3 personalization angles

4. User reviews leads di /leads page
   └─► Filter by score (A/B/C/D)
   └─► Click prospect → see full detail
   └─► Approve → trigger outreach sequence

5. Celery beat fires sequence step on schedule
   └─► Generate message via LLM with template + prospect context
   └─► Status=pending_approval (or auto-approve if setting)
   └─► User approves di /leads/queue
   └─► Send via email/WA/threads
   └─► Track delivery, open, click, reply via webhooks

6. Prospect replies → webhook → status update
   └─► Stop sequence, notify user
```

*(Detail lengkap menyusul di T2-T6)*
