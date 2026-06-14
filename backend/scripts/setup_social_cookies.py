"""
Helper: validate + install social scraper cookie files.

Run from repo root:
    docker compose exec backend python -m scripts.setup_social_cookies twitter
    docker compose exec backend python -m scripts.setup_social_cookies threads

This script:
  1. Validates the cookie file exists + has expected shape
  2. Prints what cookies are present + which are missing
  3. Copies the file to the path the scraper reads from
     (settings.twitter_cookies_path or settings.threads_cookies_path)

The cookies themselves must be obtained by the operator via
their browser (e.g. Chrome extension "Cookie Editor" → log
into x.com → export cookies → save as JSON). The format the
scraper expects:
  {
    "auth_token": "<long hex>",
    "ct0": "<long hex>",
    "twid": "<value>",          # Twitter only
    "guest_id": "<value>",
    "personalization_id": "<value>",  # Twitter only
    ... (other X cookies that Twikit accepts)
  }
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from app.core.config import settings


def _validate(path: Path) -> dict:
    """Load + check a cookies file. Returns the dict on success."""
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"❌ Not valid JSON: {e}")
    if not isinstance(data, dict):
        sys.exit(f"❌ Expected a JSON object at top level, got {type(data).__name__}")
    if not data:
        sys.exit(f"❌ Cookie file is empty")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate + install social scraper cookie files",
    )
    parser.add_argument(
        "source",
        choices=["twitter", "threads"],
        help="Which scraper to install cookies for",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the cookies JSON file (exported from your browser)",
    )
    args = parser.parse_args()

    print(f"📦 Validating cookies file: {args.path}")
    cookies = _validate(args.path)
    print(f"   ✓ Valid JSON, {len(cookies)} cookie entries")

    if args.source == "twitter":
        target = Path(settings.twitter_cookies_path)
        # Twikit (the cookie-based lib) needs at minimum auth_token + ct0.
        # Warn loudly if missing.
        required = {"auth_token", "ct0"}
        present = required & set(cookies.keys())
        missing = required - present
        if missing:
            print(f"   ⚠ Missing required cookies: {sorted(missing)}")
            print(f"   Scraping will likely fail until you re-export from x.com.")
            confirm = input("   Continue anyway? [y/N] ").strip().lower()
            if confirm != "y":
                sys.exit("Aborted.")
        # Show all cookie names (no values) for verification
        print(f"   Cookies present: {sorted(cookies.keys())[:20]}{'...' if len(cookies) > 20 else ''}")
    else:  # threads
        target = Path(settings.threads_cookies_path)
        print(f"   Cookies present: {sorted(cookies.keys())[:20]}{'...' if len(cookies) > 20 else ''}")

    # Ensure target dir exists, copy file
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.path, target)
    target.chmod(0o600)
    print(f"✓ Installed to {target}")
    print()
    print("Next steps:")
    print("  1. Restart the backend to pick up the new file:")
    print("       docker compose restart backend cf-celery-worker")
    print("  2. Trigger a test scan:")
    print("       curl -X POST .../api/v1/scraping/jobs ...")
    print("  3. Check the worker logs for 'Twitter search:' lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
