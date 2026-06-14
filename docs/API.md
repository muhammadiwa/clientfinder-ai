# ClientFinder — API Reference

> **Auto-generated REST API documentation.**

The full interactive docs are at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the backend.

For the raw OpenAPI 3.0 spec, see `/openapi.json`.

---

## Authentication

All endpoints (except `/auth/login` and `/auth/register`) require a Bearer JWT in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire after 15 minutes. Refresh tokens last 7 days. Use `/auth/refresh` to get a new access token.

---

## Endpoints (33 paths)

### Auth (`/api/v1/auth`)
- `POST /auth/login` — email + password → access + refresh tokens
- `POST /auth/register` — create new user (invite-only in production)
- `POST /auth/refresh` — exchange refresh token for new access token
- `GET /auth/me` — current user info

### Prospects (`/api/v1/prospects`)
- `GET /prospects` — list (paginated, filter by status, grade, source, search)
- `POST /prospects` — manual create
- `GET /prospects/{id}` — detail
- `PATCH /prospects/{id}` — update (status, score, notes, etc.)
- `DELETE /prospects/{id}` — soft delete
- `POST /prospects/{id}/enrich` — re-run analyst pipeline (hooks, score, pain)
- `GET /prospects/{id}/detail` — full detail (hooks, pain, audit, message history)
- `POST /prospects/{id}/score` — re-score only

### Pipeline (`/api/v1/prospects/pipeline`)
- `GET /prospects/pipeline` — kanban board view (grouped by status)

### Scraping (`/api/v1/scraping`)
- `POST /scraping/run` — start a new scraping job
- `GET /scraping/jobs` — list scraping jobs
- `GET /scraping/jobs/{id}` — job status + results

### AI (`/api/v1/ai`)
- `POST /ai/hooks/{prospect_id}` — generate hooks (uses LLM)
- `POST /ai/complete` — generic prompt completion (utility)
- `POST /ai/tech-audit` — re-run tech audit on a domain

### Outreach (`/api/v1/outreach`)
- `GET /outreach/messages` — list (filter by status, channel, prospect_grade)
- `POST /outreach/messages` — manual create
- `GET /outreach/messages/{id}` — message detail
- `PATCH /outreach/messages/{id}` — edit
- `DELETE /outreach/messages/{id}` — delete
- `POST /outreach/messages/{id}/approve` — **R10 approval gate**
- `POST /outreach/messages/{id}/reject` — reject (with reason)
- `POST /outreach/messages/{id}/send` — send (requires approved status)
- `POST /outreach/messages/{id}/generate` — AI-generate content
- `GET /outreach/stats` — hero KPI counts (13 statuses)

### Templates (`/api/v1/templates`)
- `GET /templates` — list
- `POST /templates` — create
- `GET /templates/{id}` — detail
- `PATCH /templates/{id}` — update
- `DELETE /templates/{id}` — delete

### Sequences (`/api/v1/sequences`)
- `GET /sequences` — list
- `POST /sequences` — create
- `GET /sequences/{id}` — detail (with steps)
- `PATCH /sequences/{id}` — update
- `DELETE /sequences/{id}` — delete
- `POST /sequences/{id}/start` — enroll a prospect in the sequence

### Analytics (`/api/v1/analytics`)
- `GET /analytics/overview?days=N` — all 4 KPI categories in one call (Lead Gen, Outreach, Pipeline, Operational)

### Monitoring
- `GET /healthz` — deep health check (db + redis)
- `GET /metrics` — Prometheus scrape
- `GET /openapi.json` — OpenAPI 3.0 spec
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc UI

---

## Common response format

### Success

```json
{
  "success": true,
  "data": { ... }
}
```

### Error

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": { ... }
  }
}
```

### Error codes

| Code | HTTP | Meaning |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT |
| `FORBIDDEN` | 403 | Authenticated but not authorized for this resource |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 422 | Pydantic validation failed |
| `RATE_LIMITED` | 429 | Too many requests (rate limit hit) |
| `INTERNAL_ERROR` | 500 | Server error — check logs |
| `R10_APPROVAL_REQUIRED` | 400 | Trying to send a message that's not in `approved` state |

---

## Rate limits

- **Default**: 200 requests/minute per IP or per authenticated user (whichever is more specific)
- **Auth endpoints**: 30 requests/minute (login, register, refresh)
- **Send endpoints**: 10 requests/minute (outreach send, scraping run)
- **On 429**: response includes `Retry-After: 60` header

---

## Pagination

List endpoints use cursor or offset pagination:

```bash
GET /api/v1/prospects?page=1&per_page=20
```

Response:
```json
{
  "items": [ ... ],
  "total": 247,
  "page": 1,
  "per_page": 20,
  "has_more": true
}
```

Default `per_page=20`, max `per_page=100`.

---

## SDKs

We don't ship official SDKs (single-developer project). Use `curl`, `httpx`, `axios`, or any HTTP client. Example:

```python
import httpx

with httpx.Client(base_url="https://yourdomain.com/api/v1") as client:
    r = client.post("/auth/login", json={"email": "...", "password": "..."})
    token = r.json()["data"]["access_token"]
    r = client.get("/prospects", headers={"Authorization": f"Bearer {token}"})
    prospects = r.json()["data"]["items"]
```

```javascript
const res = await axios.post("/api/v1/auth/login", { email, password });
const token = res.data.data.access_token;
const prospects = await axios.get("/api/v1/prospects", {
  headers: { Authorization: `Bearer ${token}` },
});
```
