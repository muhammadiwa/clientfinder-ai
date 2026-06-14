#!/usr/bin/env python3
"""
Refresh the vendored Swagger UI / Redoc assets.

Run from repo root:
    python backend/scripts/vendor_swagger_assets.py

Downloads the latest stable swagger-ui-dist@5 (CSS + JS) and
redoc@2 (JS) into backend/app/static/swagger-ui/. The main.py
serves these locally so /docs and /redoc work without external
CDN access (per R4: minimize external dependencies).

This is a one-shot script for re-vendoring when upgrading the
UI library versions. The committed copies are what the running
app actually serves.
"""
import urllib.request
from pathlib import Path

CDN_BASE = "https://cdn.jsdelivr.net/npm"
SWAGGER_VERSION = "swagger-ui-dist@5"
REDOC_VERSION = "redoc@2"

FILES = [
    (f"{CDN_BASE}/{SWAGGER_VERSION}/swagger-ui.css", "swagger-ui.css"),
    (f"{CDN_BASE}/{SWAGGER_VERSION}/swagger-ui-bundle.js", "swagger-ui-bundle.js"),
    (f"{CDN_BASE}/{REDOC_VERSION}/bundles/redoc.standalone.js", "redoc.standalone.js"),
]

TARGET_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "swagger-ui"


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for url, name in FILES:
        out = TARGET_DIR / name
        print(f"  fetching {url} → {out.relative_to(TARGET_DIR.parent.parent)}")
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            data = resp.read()
        out.write_bytes(data)
        print(f"    {len(data):,} bytes")
    print("Done. Restart the backend to pick up new files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
