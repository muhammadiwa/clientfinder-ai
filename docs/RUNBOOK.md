# ClientFinder — Operations Runbook

> **Production deployment + day-2 operations guide.**

---

## Table of contents

1. [Initial deployment](#initial-deployment)
2. [Daily operations](#daily-operations)
3. [Incident response](#incident-response)
4. [Scaling](#scaling)
5. [Disaster recovery](#disaster-recovery)
6. [Common tasks](#common-tasks)

---

## Initial deployment

### 1. Provision VPS

**Minimum spec** (serves 1-5 concurrent users):
- 2 vCPU
- 4 GB RAM
- 80 GB SSD
- Ubuntu 24.04 LTS
- 1 static IPv4

**Recommended** (10+ users, faster scraping):
- 4 vCPU
- 8 GB RAM
- 160 GB SSD

### 2. Install dependencies

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# DNS + SSL
sudo apt install -y caddy  # or nginx

# Firewall
sudo ufw allow 80,443,22/tcp
sudo ufw enable
```

### 3. Clone + configure

```bash
git clone https://github.com/muhammadiwa/clientfinder-ai.git /opt/clientfinder
cd /opt/clientfinder

cp .env.example .env
# Edit .env:
#   APP_ENV=production
#   APP_DEBUG=false
#   APP_SECRET=$(openssl rand -hex 32)
#   POSTGRES_PASSWORD=$(openssl rand -hex 16)
#   SMTP_PASSWORD=...
#   WAHA_API_KEY=...
#   GHP_TOKEN=ghp_...  (for auto-PR-merge)
```

### 4. Boot

```bash
docker compose up -d
docker compose logs -f backend  # wait for "Application startup complete"
```

### 5. Initialize admin

```bash
docker compose exec backend python -m app.scripts.init_admin
# Read the printed email/password IMMEDIATELY — stored in .admin_credentials (gitignored)
# SAVE to password manager, then delete the file
```

### 6. Reverse proxy (Caddy)

```bash
# /etc/caddy/Caddyfile
yourdomain.com {
    reverse_proxy localhost:80
}

sudo systemctl reload caddy
```

### 7. Set up cron (backups + renewal)

```bash
# Edit crontab
crontab -e

# Daily backup at 02:00
0 2 * * * /opt/clientfinder/scripts/backup.sh >> /var/log/cf-backup.log 2>&1

# Weekly: prune Docker images + dangling volumes (Sun 03:00)
0 3 * * 0 cd /opt/clientfinder && docker system prune -f >> /var/log/cf-prune.log 2>&1

# Monthly: cert renewal check (if not auto)
0 4 1 * * sudo systemctl reload caddy
```

---

## Daily operations

### Check service health

```bash
# All 9 containers should be Up + (healthy)
docker compose ps

# Backend health
curl -s http://localhost:8000/healthz | python3 -m json.tool
# Expected: {"status": "healthy", "db": true, "redis": true}
```

### View logs

```bash
# Tail all services
docker compose logs -f --tail=100

# Specific service
docker compose logs -f backend --tail=100

# Last 24h of errors
docker compose logs --since=24h backend | grep -E "ERROR|CRITICAL" | tail -50
```

### Restart a service

```bash
# If a service is failing:
docker compose restart backend
# If still failing:
docker compose up -d --force-recreate --no-deps backend
docker compose logs backend --tail=50
```

### Code-only changes (no rebuild)

```bash
# /app is bind-mounted from host. After editing source:
docker compose restart backend  # 5s
# In-container /app picks up new code automatically
# (Only for Python files; for dep changes or Dockerfile, rebuild)
```

---

## Incident response

### Severity levels

| Sev | Examples | Response time |
|---|---|---|
| **P0** | Service down, all users blocked | 15 min |
| **P1** | Feature broken, no workaround | 2 hr |
| **P2** | Feature broken, workaround exists | 1 day |
| **P3** | Cosmetic / nice-to-have | 1 week |

### P0: Service is down

1. `docker compose ps` — are containers running?
2. `docker compose logs backend --tail=100` — what's the error?
3. Common causes:
   - **DB connection refused** → check postgres health: `docker compose ps postgres`
   - **OOM killed** → `docker stats` to see who's using memory. Add swap, scale up, or increase VPS RAM.
   - **Port conflict** → `sudo lsof -i :8000` — kill the conflicting process
4. Roll back if needed: `git checkout <last-good-commit>` then `docker compose up -d --force-recreate`

### P1: Outreach messages not sending

1. Check Celery worker: `docker compose ps celery-worker`
2. Check worker logs: `docker compose logs celery-worker --tail=100`
3. Check SMTP creds: `docker compose exec backend python -c "from app.core.config import settings; print(settings.smtp_user, '***', bool(settings.smtp_password))"`
4. Test SMTP manually:
   ```python
   from app.services.outreach.email import test_smtp_connection
   test_smtp_connection()
   ```
5. Check openWA: `curl -X GET http://openwa-host:2785/api/sessions -H "X-Api-Key: $WAHA_API_KEY"`

### P1: High error rate

1. `curl -s http://localhost:8000/metrics | grep cf_http_requests_total` — look for 5xx counts
2. `docker compose logs backend --since=1h | grep ERROR | tail -30`
3. Check rate limit hits: `cf_rate_limit_hits_total` — if elevated, may indicate scraping abuse

### P2: Slow performance

1. `docker stats` — which service is using most resources?
2. Check DB queries: `docker compose logs postgres --tail=100 | grep slow`
3. Check Celery queue depth:
   ```bash
   docker compose exec redis redis-cli LLEN celery
   ```
4. Consider scaling (see below)

---

## Scaling

### Vertical (single VPS)

```bash
# Resize Postgres shared_buffers (in docker-compose.yml)
# Add to postgres service environment:
POSTGRES_SHARED_BUFFERS: 1GB  # = 25% of VPS RAM
POSTGRES_EFFECTIVE_CACHE_SIZE: 3GB  # ~75% of VPS RAM

# Increase Celery concurrency
# In docker-compose.yml, celery-worker command:
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=8
```

### Horizontal (multi-VPS)

For 50+ users, split:
- **VPS 1**: nginx + frontend (public)
- **VPS 2**: backend + celery (private)
- **VPS 3**: postgres + redis (private)
- **VPS 4**: searxng + openWA + Playwright (private, network-heavy)

Use Cloudflare Tunnel or WireGuard to connect them securely.

---

## Disaster recovery

### Worst case: VPS is lost

1. Provision new VPS
2. `git clone https://github.com/muhammadiwa/clientfinder-ai.git /opt/clientfinder`
3. Restore from backup: `bash scripts/restore.sh /path/to/backup.db_YYYYMMDD_HHMMSS.sql.gz.gpg`
4. Copy `.env` from password manager
5. Re-init admin: `docker compose exec backend python -m app.scripts.init_admin`
6. Update DNS to point to new VPS IP

RTO (Recovery Time Objective): ~1 hour
RPO (Recovery Point Objective): 24 hours (daily backups)

### Backup verification (do this monthly)

```bash
# Restore to a throwaway DB and compare counts
docker compose exec postgres createdb -U clientfinder test_restore
gunzip -c backups/db_latest.sql.gz | docker compose exec -T postgres psql -U clientfinder -d test_restore

# Compare row counts
docker compose exec postgres psql -U clientfinder -d test_restore -c "
  SELECT 'prospects' AS t, COUNT(*) FROM prospects
  UNION ALL SELECT 'messages', COUNT(*) FROM outreach_messages
  UNION ALL SELECT 'sequences', COUNT(*) FROM outreach_sequences
  UNION ALL SELECT 'templates', COUNT(*) FROM outreach_templates;"

# Cleanup
docker compose exec postgres dropdb -U clientfinder test_restore
```

If row counts match production (±5%), backups are healthy. If not, investigate the backup script immediately.

---

## Common tasks

### Add a new user (manually)

```bash
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def main():
    async with AsyncSessionLocal() as db:
        u = User(
            email='newuser@example.com',
            password_hash=hash_password('change-me-on-first-login'),
            full_name='New User',
            is_active=True,
            role='user',
        )
        db.add(u)
        await db.commit()
        print(f'Created user: {u.email}')

asyncio.run(main())
"
```

### Add a new LLM provider

Edit `.env`, add a new entry to `LLM_PROVIDERS_JSON`:
```json
[{"name": "groq", "api_key": "gsk_..."}, {"name": "gemini", "api_key": "AIza..."}]
```

No code change needed — `app/services/llm.py` auto-detects.

### Rotate APP_SECRET (do this quarterly)

```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -hex 32)
# 2. Edit .env, replace APP_SECRET=...
# 3. Restart (this will invalidate ALL JWTs — users must re-login)
docker compose restart backend
```

### Update the application

```bash
cd /opt/clientfinder
git pull origin develop
docker compose up -d --force-recreate
# (Cached build is fast — typically <1 min. --no-cache only for dep changes.)
```

### Tail Prometheus metrics

```bash
# Request volume
curl -s http://localhost:8000/metrics | grep cf_http_requests_total

# Latency (95th percentile)
curl -s http://localhost:8000/metrics | grep cf_http_request_duration_seconds_bucket | head

# DB + Redis health
curl -s http://localhost:8000/metrics | grep -E "cf_db_up|cf_redis_up"
```

### Set up Grafana (optional)

1. `docker compose -f docker-compose.monitoring.yml up -d`
2. Open http://localhost:3000 (admin/admin — change immediately)
3. Add Prometheus data source: http://prometheus:9090
4. Import dashboard: `cf_http_requests_total`, `cf_http_request_duration_seconds`, `cf_db_up`, `cf_redis_up`, `cf_rate_limit_hits_total`

---

## Contact

For emergencies, contact: [your contact info]

For non-urgent issues, file a GitHub issue.
