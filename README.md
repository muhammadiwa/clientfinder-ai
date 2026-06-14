# ClientFinder AI Agent

> **AI-powered lead generation + outreach platform for freelance software developers.**

Self-hosted, free-tier stack, Bahasa Indonesia focus, human-in-the-loop outreach.

---

## What it does

1. **Discovers** Indonesian UMKM prospects (klinik gigi, kafe, salon, retail) who likely need software (web, mobile, ERP, AI)
2. **Analyzes** each prospect: tech stack audit, pain point detection, 0-100 scoring
3. **Drafts** personalized outreach (Email + WhatsApp) for human review
4. **Approves** before send (R10 — every outbound message requires human approval)
5. **Tracks** delivery + reply + win rate in the analytics dashboard

---

## Quick start (5 minutes)

```bash
# 1. Clone + enter
git clone https://github.com/muhammadiwa/clientfinder-ai.git
cd clientfinder-ai

# 2. Configure secrets
cp .env.example .env
# Edit .env — at minimum set APP_SECRET, POSTGRES_PASSWORD

# 3. Boot
docker compose up -d
# Wait ~30s for all 9 containers to start

# 4. Initialize database + create first user
docker compose exec backend python -m app.scripts.init_admin
# Saves admin email/password to .admin_credentials (gitignored)

# 5. Open
open http://localhost
# Login with the admin email/password printed above
```

---

## Architecture

```
┌───────────  React (Vite + TypeScript)  ───────────┐
│  /dashboard  /scout  /prospects  /pipeline        │
│  /outreach   /analytics   /settings                │
└────────────────────┬───────────────────────────────┘
                     │  axios + JWT
                     ▼
┌───────────  FastAPI (Python 3.12)  ───────────────┐
│  /api/v1/auth  /prospects  /scraping  /ai         │
│  /outreach  /templates  /sequences  /analytics    │
│  /healthz  /metrics  /docs  /openapi.json         │
└────────┬──────┬─────────┬──────────┬──────────────┘
         │      │         │          │
         ▼      ▼         ▼          ▼
     ┌────┐ ┌─────┐ ┌────────┐ ┌──────────┐
     │ PG │ │Redis│ │ Celery │ │ Playwright│
     └────┘ └─────┘ └────────┘ └──────────┘
                                        │
                                        ▼
                              ┌──────────────┐
                              │   searxng    │
                              │   openWA     │
                              │  TokenRouter │
                              └──────────────┘
```

9 Docker services: `frontend` · `backend` · `postgres` · `redis` · `celery-worker` · `celery-beat` · `playwright` · `searxng` · `nginx`

---

## Stack (all free-tier or self-hosted)

| Layer | Tool | Cost |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Free |
| Frontend | React 19 + Vite + TS | Free |
| Database | PostgreSQL 16 | Free (self-hosted) |
| Cache + broker | Redis 7 | Free |
| Task queue | Celery | Free |
| Scraping | Playwright (Chromium) | Free |
| LLM | TokenRouter primary + Groq + Gemini | Free tier |
| Search engine | searxng | Free (self-hosted) |
| Email | Postfix SMTP (self-host) + Zoho fallback | Free |
| WhatsApp | openWA (user-deployed) | Free |
| Monitoring | Prometheus + Grafana (T8) | Free |
| Backups | Local cron + rclone (T8) | Free |

**Total cost: $0/month.** Only LLM API calls (TokenRouter / Groq / Gemini free tier) leave your VPS.

---

## Key principles (locked in D1-D133)

- **R1**: All tools free. No paid SaaS without explicit approval.
- **R2**: Indonesia-only. Bahasa Indonesia for all user-facing copy.
- **R3**: UMKM niche only. Klinik Gigi + Klinik Kecantikan + F&B chain (v1).
- **R6**: Production-ready, not MVP. Docker + tests + monitoring + backups.
- **R9**: Outreach v1 = Email + WhatsApp. Threads/LinkedIn v2.
- **R10**: **Every** outbound message requires human approval. Non-negotiable.
- **R13**: Gitflow-lite. `main` = production. `develop` = integration. `feature/*` = per-task.
- **R14**: Push + auto-PR-merge after every logical group.
- **R16**: **All** API keys in `.env` (gitignored), never hardcoded in source.

---

## Development workflow

```bash
# Always work on a feature branch
git checkout develop
git pull origin develop
git checkout -b feature/my-task

# Edit code, commit (conventional commits)
git commit -m "feat(T9): add retention cohort chart"

# Push + auto-merge to develop
git push -u origin feature/my-task
GITHUB_TOKEN=... bash scripts/auto-pr-merge.sh feature/my-task
# (auto-creates PR to develop + squash-merge)
```

See [docs/AGENTS.md](docs/AGENTS.md) for the full agent spec.

---

## Production deployment

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for the complete deployment + incident response guide.

TL;DR:
1. Provision VPS (Ubuntu 24.04, 2 vCPU / 4 GB RAM / 80 GB SSD)
2. Install Docker + Docker Compose
3. Clone repo, configure `.env` (set `APP_ENV=production`)
4. Set up cron for backups: `0 2 * * * /path/to/backup.sh`
5. Set up reverse proxy (Caddy / nginx + Let's Encrypt)
6. Set up monitoring (Prometheus scrape /metrics + Grafana dashboards)

---

## Documentation

- [docs/AGENTS.md](docs/AGENTS.md) — 10-agent system spec
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — deployment + incident response
- [docs/SECURITY.md](docs/SECURITY.md) — security policy + threat model
- [docs/BACKUP.md](docs/BACKUP.md) — backup + restore procedures
- [docs/API.md](docs/API.md) — REST API reference (auto-generated from OpenAPI)

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

This is a solo project (single developer / "Juragan" workflow). PRs welcome for bug fixes + small improvements. For major features, open an issue first.

**Status: 8/8 phases done.** T1 (infra) → T2 (backend) → T3 (frontend) → T4 (scout) → T5 (analyst) → T6 (outreach) → T7 (analytics) → T8 (production hardening).
