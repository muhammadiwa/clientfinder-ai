# ClientFinder — Security Policy

> **Threat model, security controls, and incident response for security events.**

---

## Threat model

### Assets

1. **Prospect PII** — business names, addresses, phone numbers, emails
2. **Outreach messages** — proprietary copy, lead generation strategies
3. **User credentials** — admin password, JWT tokens
4. **API keys** — LLM providers (TokenRouter, Groq, Gemini), SMTP, WhatsApp
5. **Source code** — proprietary agent logic, prompt engineering
6. **Database** — all prospect + message data

### Adversaries

| Adversary | Capability | Motivation |
|---|---|---|
| **Opportunistic attacker** | Script kiddie, automated scanners | Try default creds, find exposed services |
| **Competitor** | Has your domain knowledge, can craft targeted attacks | Steal prospect list, sabotage pipeline |
| **Malicious prospect** | Has their own data in your system | Extract their data, send abuse, dox admin |
| **Insider** | Single trusted user (Juragan) | Accidental disclosure, misconfig |

### Out of scope

- Nation-state attackers (assume VPS provider protects against this)
- Physical access to the VPS
- Browser-side attacks on admin (XSS via prospect data) — admin is trusted

---

## Security controls (defense in depth)

### 1. Network

- **Firewall**: only ports 22 (SSH), 80 (HTTP), 443 (HTTPS) open
- **Reverse proxy**: Caddy auto-issues Let's Encrypt cert + HSTS
- **Internal services**: bind to 127.0.0.1 or `cf-net` Docker network (not exposed to host)
- **No public Postgres/Redis**: never expose 5432/6379 to the internet

### 2. Application

- **Authentication**: bcrypt-hashed passwords (rounds=12), JWT (HS256) with 15min access / 7d refresh
- **Authorization**: role-based (`admin` / `user`), enforced via `app/core/deps.py`
- **Rate limiting**: 200 req/min per user-or-IP, 429 on exceed
- **Security headers** (T8):
  - HSTS: `max-age=31536000; includeSubDomains`
  - X-Frame-Options: `DENY`
  - X-Content-Type-Options: `nosniff`
  - CSP: `default-src 'self'; frame-ancestors 'none'`
  - Referrer-Policy: `strict-origin-when-cross-origin`
  - Permissions-Policy: deny camera/mic/geo/payment
- **CORS**: locked to specific origins (no wildcard)
- **Input validation**: Pydantic schemas on every endpoint
- **SQL injection**: SQLAlchemy ORM + parameter binding (no string concat)

### 3. Secrets

- **All API keys in `.env`** (gitignored) — never hardcoded (R16)
- **Secret validation at boot** (T8): refuses to start with default values in non-local env
- **Minimum lengths enforced**: APP_SECRET ≥ 32 chars, SMTP_PASSWORD ≥ 8
- **Encrypted backups**: AES-256 symmetric with `BACKUP_PASSPHRASE` env var

### 4. Data

- **Encryption at rest**: PostgreSQL data directory is on encrypted disk (LUKS) on production VPS
- **Encryption in transit**: TLS 1.2+ enforced by Caddy
- **Backups**: encrypted with `gpg --symmetric --cipher-algo AES256`
- **PII handling**: prospect data only stored in DB; not exported to external services (except LLM for analysis)

### 5. Operational

- **Container isolation**: each service runs as non-root user
- **Image updates**: rebuild monthly (`docker compose pull && docker compose up -d`)
- **Dependency audit**: `pip-audit` on backend, `npm audit` on frontend (CI)
- **Logs**: structured JSON, no PII in logs, 30-day retention
- **Backups**: daily at 02:00, 30-day retention, monthly restore verification

---

## Security headers (verified in production)

```bash
$ curl -sI https://yourdomain.com/health | grep -iE "strict-transport|x-frame|content-security|referrer"
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Incident response (security)

### Severity

| Sev | Examples | Response time |
|---|---|---|
| **P0-CRITICAL** | RCE, data breach, admin creds leaked | 1 hour |
| **P1-HIGH** | Auth bypass, PII exfil possible | 4 hours |
| **P2-MED** | DoS, scraping abuse | 1 day |
| **P3-LOW** | Security header missing, info disclosure | 1 week |

### P0: Data breach

1. **Contain**:
   - `docker compose down` (stop all services)
   - Rotate ALL secrets in `.env` (APP_SECRET, DB password, API keys)
   - Save forensic copies: `docker compose logs > /tmp/logs_$(date +%s).log`
2. **Assess**:
   - What's the attack vector?
   - What data was accessed?
3. **Eradicate**: patch the vulnerability
4. **Recover**: `docker compose up -d`, force re-login all users
5. **Notify**:
   - If prospect PII was breached: notify affected prospects within 72h (GDPR / UU PDP)
   - File GitHub security advisory

### P1: Suspected credential leak

1. **Rotate**:
   - Change all admin passwords
   - Rotate APP_SECRET (invalidates all JWTs)
   - Rotate LLM API keys, SMTP password, WAHA_API_KEY
2. **Audit**:
   - `docker compose logs auth.* | grep "login:" | tail -50` — look for unfamiliar IPs
   - Check `/metrics` for unusual request patterns
3. **Notify**: file security advisory if exploit was used

### P2: Rate limit / abuse

1. **Identify**: `cf_rate_limit_hits_total{path="/api/v1/scraping/run"}` — if spiking, may indicate abuse
2. **Mitigate**: lower the rate limit temporarily (`@limiter.limit("10/minute")`)
3. **Block**: add IP block to `iptables` or fail2ban
4. **Review**: log the IP, add to deny list if persistent

---

## Reporting a vulnerability

Email: [your security contact email]
PGP key: [fingerprint]

We aim to acknowledge within 48 hours and provide a fix timeline within 7 days.

**Scope:**
- Backend API (FastAPI)
- Frontend SPA (React)
- Celery workers
- Docker deployment scripts

**Out of scope:**
- OpenWA (third-party, file upstream)
- searxng (third-party)
- LLM provider endpoints (third-party)
- VPS provider infrastructure

---

## Compliance

This is a single-tenant self-hosted system. **You** are the data controller.

If you collect Indonesian prospect data, you may be subject to:
- **UU PDP** (Undang-Undang Pelindungan Data Pribadi) — Indonesia's data protection law
- **GDPR** (if any EU residents in your prospect list)

**Recommendations:**
- Add a privacy policy to your outreach (link in email footer)
- Provide an opt-out mechanism (e.g., "Reply STOP to unsubscribe")
- Keep a record of consent (or legitimate interest) for each prospect
- Delete prospect data on request within 30 days

The current v1 does **not** include these by default. Add them before scaling to 100+ prospects.
