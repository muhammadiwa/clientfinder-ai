# Vendored Swagger UI / Redoc assets

These files are served locally by `app.main` at `/static/swagger-ui/...`
so that `/docs` and `/redoc` work without external CDN access.

## Why

FastAPI's default docs HTML loads CSS+JS from `cdn.jsdelivr.net`. Behind
a firewall, on a corporate network, or in any environment that can't
reach the CDN, the docs UI renders as a wall of unstyled HTML — useless.

Per R4 ("minimize external dependencies; only LLM API calls go off-box")
and R6 (production-ready, not MVP), we self-host the assets.

## What's here

- `swagger-ui.css` (179 KB) — styles for /docs
- `swagger-ui-bundle.js` (1.5 MB) — JS for /docs
- `redoc.standalone.js` (1.1 MB) — JS for /redoc

Total: ~2.8 MB committed to the repo.

## Refreshing

```bash
python backend/scripts/vendor_swagger_assets.py
```

Then restart the backend to pick up the new files.
